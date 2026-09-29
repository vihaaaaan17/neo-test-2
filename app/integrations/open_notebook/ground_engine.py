import logging
import asyncio
import json
from uuid import UUID
from typing import Optional, List, Dict, Any, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from app.integrations.open_notebook.client import OpenNotebookClient
from app.integrations.open_notebook.citation_mapper import map_citations
from app.models.open_notebook_binding import OpenNotebookWorkspaceBinding, OpenNotebookConversationBinding

logger = logging.getLogger(__name__)


class OpenNotebookGroundEngine:
    """
    Facade for interacting with Open Notebook's retrieval, asking, and conversational streaming APIs.
    Guarantees strict Ground isolation: Ground execution is source-grounded and conversational,
    strictly rejecting any ResearchContext or unverified research state.
    """

    def __init__(self, workspace_id: Optional[UUID] = None, http_client = None, client: Optional[OpenNotebookClient] = None):
        self.workspace_id = workspace_id
        self.client = client or OpenNotebookClient(
            workspace_id=str(workspace_id) if workspace_id else None,
            http_client=http_client
        )
        self.default_strategy_model = "gpt-4o-mini"
        self.default_answer_model = "gpt-4o"
        self.default_final_answer_model = "gpt-4o"

    @staticmethod
    def _validate_ground_isolation(ground_context: Any = None) -> None:
        """
        Enforce strict isolation: Ground execution must never receive research context.
        """
        if ground_context is not None:
            if (
                hasattr(ground_context, "research_run_id") or
                hasattr(ground_context, "working_memory") or
                hasattr(ground_context, "output_graph") or
                type(ground_context).__name__ == "ResearchContext"
            ):
                raise ValueError(
                    "Ground engine rejects ResearchContext: Ground execution must be strictly isolated to GroundContext."
                )

    async def _get_active_binding(self, workspace_id: UUID, db: AsyncSession) -> OpenNotebookWorkspaceBinding:
        stmt = select(OpenNotebookWorkspaceBinding).where(
            OpenNotebookWorkspaceBinding.workspace_id == workspace_id,
            OpenNotebookWorkspaceBinding.status.in_(["active", "ACTIVE"])
        )
        result = await db.execute(stmt)
        binding = result.scalars().first()
        if not binding:
            raise HTTPException(
                status_code=400,
                detail="Workspace does not have an active Open Notebook binding."
            )
        return binding

    async def _resolve_citations(
        self,
        query: str,
        workspace_id: UUID,
        db: AsyncSession,
        source_scope: Optional[List[Any]] = None,
        extra_upstream_ids: Optional[List[str]] = None
    ) -> tuple[List[UUID], bool]:
        try:
            search_results = await self.client.search(query=query)
        except Exception as e:
            logger.warning("Open Notebook search failed during citation resolution: %s", e)
            search_results = []
        upstream_ids = [res.get("id") for res in search_results if "id" in res] if search_results else []
        if extra_upstream_ids:
            upstream_ids = list(set(upstream_ids + extra_upstream_ids))

        valid_source_ids, partial = await map_citations(upstream_ids, workspace_id, db)

        if source_scope:
            scope_set = {UUID(str(s)) for s in source_scope}
            initial_count = len(valid_source_ids)
            valid_source_ids = [s for s in valid_source_ids if s in scope_set]
            if len(valid_source_ids) < initial_count:
                partial = True

        if upstream_ids and not valid_source_ids:
            raise HTTPException(
                status_code=422,
                detail="ground_provenance_failure: Zero mapped canonical evidence."
            )

        return valid_source_ids, partial

    async def _get_or_create_conversation_session(
        self,
        conversation_id: UUID,
        notebook_id: str,
        db: AsyncSession
    ) -> tuple[OpenNotebookConversationBinding, str]:
        conv_bind_stmt = select(OpenNotebookConversationBinding).where(
            OpenNotebookConversationBinding.conversation_id == conversation_id
        )
        conv_res = await db.execute(conv_bind_stmt)
        conv_binding = conv_res.scalars().first()

        if not conv_binding:
            session_id = await self.client.create_chat_session(notebook_id)
            conv_binding = OpenNotebookConversationBinding(
                conversation_id=conversation_id,
                open_notebook_session_id=session_id
            )
            db.add(conv_binding)
            await db.commit()
            await db.refresh(conv_binding)
        else:
            session_id = conv_binding.open_notebook_session_id

        return conv_binding, session_id

    async def run(
        self,
        workspace_id: UUID,
        query: str,
        db: AsyncSession,
        conversation_id: Optional[UUID] = None,
        turn_id: Optional[UUID] = None,
        source_scope: Optional[list] = None,
        ground_context: Optional[Any] = None
    ) -> dict:
        logger.info(f"Running OpenNotebookGroundEngine for query: {query}")
        self._validate_ground_isolation(ground_context)

        if ground_context is not None:
            if source_scope is None and hasattr(ground_context, "source_scope"):
                source_scope = ground_context.source_scope
            if conversation_id is None and hasattr(ground_context, "conversation_id"):
                conversation_id = ground_context.conversation_id

        binding = await self._get_active_binding(workspace_id, db)
        notebook_id = binding.open_notebook_notebook_id

        try:
            # 1. Concurrently search and ask/chat
            if conversation_id and hasattr(self.client, "chat_execute"):
                conv_binding, session_id = await self._get_or_create_conversation_session(
                    conversation_id, notebook_id, db
                )

                answer_text = ""
                extra_evidence = []
                for attempt in range(2):
                    try:
                        results = await asyncio.gather(
                            self.client.search(query=query),
                            self.client.chat_execute(
                                session_id=session_id,
                                notebook_id=notebook_id,
                                message=query
                            ),
                            return_exceptions=True
                        )
                        search_results, chat_res = results[0], results[1]
                        if isinstance(chat_res, Exception):
                            raise chat_res
                        if isinstance(search_results, Exception):
                            logger.warning("Open Notebook search failed: %s", search_results)
                            search_results = []
                        answer_text = chat_res.get("answer", "")
                        extra_evidence = chat_res.get("evidence", [])
                        break
                    except HTTPException as e:
                        is_session_lost = (
                            e.status_code in [400, 404, 409] and (
                                "session_state_lost" in str(e.detail) or
                                "conversation_session_expired" in str(e.detail)
                            )
                        )
                        if is_session_lost and attempt == 0:
                            session_id = await self.client.create_chat_session(notebook_id)
                            conv_binding.open_notebook_session_id = session_id
                            await db.commit()
                            continue
                        raise

                upstream_ids = [res.get("id") for res in search_results if "id" in res] if search_results else []
                if extra_evidence:
                    extracted = [
                        e.get("source_id") or e.get("id") if isinstance(e, dict) else str(e)
                        for e in extra_evidence
                    ]
                    upstream_ids = list(set(upstream_ids + [x for x in extracted if x]))
                valid_source_ids, partial = await map_citations(upstream_ids, workspace_id, db)
                if not valid_source_ids and extra_evidence:
                    valid_source_ids = extra_evidence
                if source_scope:
                    scope_set = {UUID(str(s)) for s in source_scope}
                    initial_count = len(valid_source_ids)
                    valid_source_ids = [s for s in valid_source_ids if (isinstance(s, UUID) and s in scope_set) or (isinstance(s, dict) and UUID(str(s.get("source_id"))) in scope_set)]
                    if len(valid_source_ids) < initial_count:
                        partial = True

                if upstream_ids and not valid_source_ids and not extra_evidence:
                    raise HTTPException(
                        status_code=422,
                        detail="ground_provenance_failure: Zero mapped canonical evidence."
                    )

                return {
                    "answer": answer_text,
                    "evidence": valid_source_ids,
                    "is_grounded": True,
                    "provenance_status": "partial" if partial else "full"
                }

            # Standalone unary run (search + ask_simple)
            default_models = await self.client.get_default_models()
            model_name = default_models.get("default_chat_model", self.default_answer_model)
            search_task = self.client.search(query=query)
            ask_task = self.client.ask_simple(
                question=query,
                strategy_model=model_name,
                answer_model=model_name,
                final_answer_model=model_name
            )
            search_results, ask_result = await asyncio.gather(search_task, ask_task)

            upstream_ids = [res.get("id") for res in search_results if "id" in res] if search_results else []
            valid_source_ids, partial = await map_citations(upstream_ids, workspace_id, db)
            if source_scope:
                scope_set = {UUID(str(s)) for s in source_scope}
                initial_count = len(valid_source_ids)
                valid_source_ids = [s for s in valid_source_ids if s in scope_set]
                if len(valid_source_ids) < initial_count:
                    partial = True

            if upstream_ids and not valid_source_ids:
                raise HTTPException(
                    status_code=422,
                    detail="ground_provenance_failure: Zero mapped canonical evidence."
                )

            return {
                "answer": ask_result.get("answer", ""),
                "evidence": valid_source_ids,
                "is_grounded": True,
                "provenance_status": "partial" if partial else "full"
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Open Notebook Engine failed: {str(e)}")
            raise HTTPException(status_code=503, detail="Upstream ground engine unavailable or synthesis failed.")

    async def astream(
        self,
        workspace_id: UUID,
        query: str,
        db: AsyncSession,
        conversation_id: Optional[UUID] = None,
        turn_id: Optional[UUID] = None,
        source_scope: Optional[list] = None,
        ground_context: Optional[Any] = None
    ) -> AsyncGenerator[dict, None]:
        logger.info(f"Running OpenNotebookGroundEngine.astream for query: {query}")
        self._validate_ground_isolation(ground_context)

        if ground_context is not None:
            if source_scope is None and hasattr(ground_context, "source_scope"):
                source_scope = ground_context.source_scope
            if conversation_id is None and hasattr(ground_context, "conversation_id"):
                conversation_id = ground_context.conversation_id

        binding = await self._get_active_binding(workspace_id, db)
        notebook_id = binding.open_notebook_notebook_id

        # 1. Resolve citations & provenance upfront
        try:
            valid_source_ids, partial = await self._resolve_citations(
                query=query,
                workspace_id=workspace_id,
                db=db,
                source_scope=source_scope
            )
        except Exception as e:
            logger.warning("Upfront citation resolution skipped: %s", e)
            valid_source_ids, partial = [], False

        prov_status = "partial" if partial else "full"
        yield {
            "event": "citation",
            "type": "citation",
            "evidence": valid_source_ids,
            "provenance_status": prov_status,
            "data": {
                "evidence": [str(e) for e in valid_source_ids],
                "provenance_status": prov_status
            }
        }

        # 2. Stream tokens
        full_answer: List[str] = []

        if conversation_id:
            conv_binding, session_id = await self._get_or_create_conversation_session(
                conversation_id, notebook_id, db
            )

            for attempt in range(2):
                try:
                    full_answer = []
                    if hasattr(self.client, "chat_stream"):
                        async for chunk in self.client.chat_stream(
                            session_id=session_id,
                            notebook_id=notebook_id,
                            message=query
                        ):
                            ev_type = chunk.get("event") or chunk.get("type") or "token"
                            ev_data = chunk.get("data") or {}
                            if ev_type in ["token", "answer"]:
                                token = ev_data.get("token") or ev_data.get("content") or chunk.get("content") or ""
                                if token:
                                    full_answer.append(token)
                                    yield {
                                        "event": "token",
                                        "type": "token",
                                        "content": token,
                                        "data": {"content": token}
                                    }
                            elif ev_type == "strategy":
                                yield {
                                    "event": "strategy",
                                    "type": "strategy",
                                    "data": ev_data
                                }
                            elif ev_type == "done":
                                ans = ev_data.get("answer") or chunk.get("answer")
                                if ans and not full_answer:
                                    full_answer.append(ans)
                    else:
                        chat_res = await self.client.chat_execute(
                            session_id=session_id,
                            notebook_id=notebook_id,
                            message=query
                        )
                        ans = chat_res.get("answer", "")
                        if ans:
                            full_answer.append(ans)
                            yield {
                                "event": "token",
                                "type": "token",
                                "content": ans,
                                "data": {"content": ans}
                            }
                    break
                except HTTPException as e:
                    is_session_lost = (
                        e.status_code in [400, 404, 409] and (
                            "session_state_lost" in str(e.detail) or
                            "conversation_session_expired" in str(e.detail)
                        )
                    )
                    if is_session_lost and attempt == 0:
                        session_id = await self.client.create_chat_session(notebook_id)
                        conv_binding.open_notebook_session_id = session_id
                        await db.commit()
                        continue
                    raise
        else:
            default_models = await self.client.get_default_models()
            strategy_model = default_models.get("default_chat_model", self.default_strategy_model)
            answer_model = default_models.get("default_chat_model", self.default_answer_model)
            final_answer_model = default_models.get("default_chat_model", self.default_final_answer_model)

            if hasattr(self.client, "ask_stream"):
                async for sse_chunk in self.client.ask_stream(
                    question=query,
                    strategy_model=strategy_model,
                    answer_model=answer_model,
                    final_answer_model=final_answer_model
                ):
                    if "data: " in sse_chunk:
                        for line in sse_chunk.splitlines():
                            if line.startswith("data: "):
                                try:
                                    payload = json.loads(line[6:])
                                    content = payload.get("content") or payload.get("token") or payload.get("final_answer")
                                    if content:
                                        full_answer.append(content)
                                        yield {
                                            "event": "token",
                                            "type": "token",
                                            "content": content,
                                            "data": {"content": content}
                                        }
                                except Exception:
                                    pass
            else:
                ask_res = await self.client.ask_simple(
                    question=query,
                    strategy_model=strategy_model,
                    answer_model=answer_model,
                    final_answer_model=final_answer_model
                )
                ans = ask_res.get("answer", "")
                if ans:
                    full_answer.append(ans)
                    yield {
                        "event": "token",
                        "type": "token",
                        "content": ans,
                        "data": {"content": ans}
                    }

        # 3. Final done event
        final_answer_text = "".join(full_answer)
        yield {
            "event": "done",
            "type": "done",
            "answer": final_answer_text,
            "evidence": valid_source_ids,
            "provenance_status": prov_status,
            "data": {
                "status": "completed",
                "assistant_message": final_answer_text,
                "answer": final_answer_text,
                "ground_evidence_refs": [str(e) for e in valid_source_ids],
                "evidence": [str(e) for e in valid_source_ids],
                "provenance_status": prov_status
            }
        }
