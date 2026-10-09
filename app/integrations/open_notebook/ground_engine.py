import re
import os
import logging
import asyncio
import json
from uuid import UUID
from typing import Optional, List, Dict, Any, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from app.integrations.open_notebook.client import OpenNotebookClient
from app.integrations.open_notebook.citation_mapper import map_citations, map_canonical_sources_to_upstream, list_workspace_upstream_source_ids
from app.models.open_notebook_binding import OpenNotebookWorkspaceBinding, OpenNotebookConversationBinding

logger = logging.getLogger(__name__)



from app.integrations.open_notebook.ground_evidence import inline_citation_ids, resolve_ground_evidence  # noqa: E402


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
            try:
                res = await self.client.create_notebook(name=f"Workspace-{str(workspace_id)[:8]}")
                on_notebook_id = res.get("id") or str(res)
                from app.repositories.open_notebook import OpenNotebookRepository
                repo = OpenNotebookRepository(db)
                binding = await repo.create_workspace_binding(workspace_id, on_notebook_id)
                await db.commit()
            except Exception as e:
                logger.warning("Could not lazily bind Open Notebook workspace: %s", e)
                raise HTTPException(
                    status_code=400,
                    detail=f"Workspace does not have an active Open Notebook binding: {e}"
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

    @staticmethod
    def _grounded_result(answer: str, resolution: dict) -> dict:
        """
        Map a citation resolution onto the Ground result:
          * some citations resolve -> evidence = those canonical sources (status full/partial; unresolved ones listed);
          * citations exist but NONE resolve -> fail closed: the answer cites sources that are not this workspace's
            (Open Notebook's search spans every tenant), so it is rejected with the unresolved ids named;
          * no citations at all -> the answer is kept but marked provenance "none" with no evidence - it is never
            presented as verified (the UI flags it as not verified against the workspace's sources).
        """
        if not resolution["source_ids"] and resolution["unresolved"]:
            unresolved = ", ".join(u["upstream_id"] for u in resolution["unresolved"])
            raise HTTPException(
                status_code=422,
                detail=f"ground_provenance_failure: Zero mapped canonical evidence. Unresolved citations: {unresolved}",
            )
        return {
            "answer": answer,
            "evidence": resolution["source_ids"],
            "evidence_details": resolution["evidence"],
            "unresolved_citations": resolution["unresolved"],
            "is_grounded": True,
            "provenance_status": resolution["provenance_status"],
        }

    async def _search_hits(self, query: str, mapped_upstream_ids: list) -> list:
        try:
            hits = await self.client.search(query=query)
        except Exception as e:
            logger.warning("Open Notebook search failed: %s", e)
            return []
        if not isinstance(hits, list):
            return []
        if mapped_upstream_ids:
            hits = [h for h in hits if isinstance(h, dict) and h.get("id") in mapped_upstream_ids]
        return hits

    async def _get_or_create_conversation_session(
        self,
        conversation_id: UUID,
        notebook_id: str,
        db: AsyncSession
    ) -> tuple[OpenNotebookConversationBinding, str]:
        conv_bind_stmt = select(OpenNotebookConversationBinding).where(
            OpenNotebookConversationBinding.conversation_id == conversation_id
        ).with_for_update()
        conv_res = await db.execute(conv_bind_stmt)
        conv_binding = conv_res.scalars().first()

        if not conv_binding:
            session_id = await self.client.create_chat_session(notebook_id)
            conv_binding = OpenNotebookConversationBinding(
                conversation_id=conversation_id,
                open_notebook_session_id=session_id
            )
            db.add(conv_binding)
            try:
                await db.commit()
                await db.refresh(conv_binding)
            except Exception:
                await db.rollback()
                conv_res = await db.execute(
                    select(OpenNotebookConversationBinding).where(
                        OpenNotebookConversationBinding.conversation_id == conversation_id
                    )
                )
                conv_binding = conv_res.scalars().first()
                if conv_binding:
                    session_id = conv_binding.open_notebook_session_id
                else:
                    raise
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

        # Map canonical source scope to Open Notebook upstream IDs
        mapped_upstream_ids: List[str] = []
        if source_scope:
            canonical_uuids = [
                UUID(str(s.get("source_id") or s.get("id"))) if isinstance(s, dict) else UUID(str(s))
                for s in source_scope
                if (isinstance(s, dict) and (s.get("source_id") or s.get("id"))) or (not isinstance(s, dict) and s)
            ]
            if canonical_uuids:
                mapped_upstream_ids = await map_canonical_sources_to_upstream(
                    canonical_uuids,
                    workspace_id,
                    db
                )
                if not mapped_upstream_ids:
                    raise HTTPException(
                        status_code=422,
                        detail="ground_provenance_failure: Zero mapped canonical evidence."
                    )

        # Without an explicit scope, ground on every projected source in the workspace;
        # Open Notebook otherwise sends only source titles to the model.
        context_ids = mapped_upstream_ids or await list_workspace_upstream_source_ids(workspace_id, db)
        context_config = {
            "sources": {
                sid: "full content" for sid in context_ids
            }
        } if context_ids else {}

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
                                message=query,
                                context_config=context_config
                            ),
                            return_exceptions=True
                        )
                        search_results, chat_res = results[0], results[1]
                        if isinstance(chat_res, Exception):
                            raise chat_res
                        if isinstance(search_results, Exception):
                            logger.warning("Open Notebook search failed: %s", search_results)
                            search_results = []
                        elif mapped_upstream_ids and isinstance(search_results, list):
                            search_results = [r for r in search_results if isinstance(r, dict) and r.get("id") in mapped_upstream_ids]
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

                if not isinstance(answer_text, str):
                    raise HTTPException(status_code=502, detail="ground_upstream_invalid_response")
                resolution = await resolve_ground_evidence(
                    answer=answer_text, workspace_id=workspace_id, db=db,
                    search_hits=search_results if isinstance(search_results, list) else [],
                    chat_evidence=extra_evidence if isinstance(extra_evidence, list) else [],
                    source_scope=source_scope,
                )
                return self._grounded_result(answer_text, resolution)

            # Standalone unary run (search + ask_simple)
            default_models = await self.client.get_default_models()
            model_name = default_models.get("default_chat_model") or self.default_answer_model
            search_task = self.client.search(query=query)
            ask_task = self.client.ask_simple(
                question=query,
                strategy_model=model_name,
                answer_model=model_name,
                final_answer_model=model_name
            )
            search_results, ask_result = await asyncio.gather(search_task, ask_task)

            answer = ask_result.get("answer", "") if isinstance(ask_result, dict) else ""
            resolution = await resolve_ground_evidence(
                answer=answer, workspace_id=workspace_id, db=db,
                search_hits=search_results if isinstance(search_results, list) else [],
                source_scope=source_scope,
            )
            return self._grounded_result(answer, resolution)
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

        # Map canonical source scope to Open Notebook upstream IDs
        mapped_upstream_ids: List[str] = []
        if source_scope:
            canonical_uuids = [
                UUID(str(s.get("source_id") or s.get("id"))) if isinstance(s, dict) else UUID(str(s))
                for s in source_scope
                if (isinstance(s, dict) and (s.get("source_id") or s.get("id"))) or (not isinstance(s, dict) and s)
            ]
            if canonical_uuids:
                mapped_upstream_ids = await map_canonical_sources_to_upstream(
                    canonical_uuids,
                    workspace_id,
                    db
                )
                if not mapped_upstream_ids:
                    raise HTTPException(
                        status_code=422,
                        detail="ground_provenance_failure: Zero mapped canonical evidence."
                    )

        # Without an explicit scope, ground on every projected source in the workspace;
        # Open Notebook otherwise sends only source titles to the model.
        context_ids = mapped_upstream_ids or await list_workspace_upstream_source_ids(workspace_id, db)
        context_config = {
            "sources": {
                sid: "full content" for sid in context_ids
            }
        } if context_ids else {}

        # Citations are resolved once the full answer is known (its inline [source:...] citations are the primary signal).

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
                            message=query,
                            context_config=context_config
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
            strategy_model = default_models.get("default_chat_model") or self.default_strategy_model
            answer_model = default_models.get("default_chat_model") or self.default_answer_model
            final_answer_model = default_models.get("default_chat_model") or self.default_final_answer_model

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

        # 3. Resolve canonical evidence for the complete answer (fail closed), then the final done event
        final_answer_text = "".join(full_answer)
        resolution = await resolve_ground_evidence(
            answer=final_answer_text, workspace_id=workspace_id, db=db,
            search_hits=await self._search_hits(query, mapped_upstream_ids), source_scope=source_scope,
        )
        result = self._grounded_result(final_answer_text, resolution)
        valid_source_ids, prov_status = result["evidence"], result["provenance_status"]
        yield {
            "event": "citation",
            "type": "citation",
            "evidence": valid_source_ids,
            "evidence_details": result["evidence_details"],
            "unresolved_citations": result["unresolved_citations"],
            "provenance_status": prov_status,
            "data": {"evidence": [str(e) for e in valid_source_ids], "provenance_status": prov_status},
        }
        yield {
            "event": "done",
            "type": "done",
            "answer": final_answer_text,
            "evidence": valid_source_ids,
            "evidence_details": result["evidence_details"],
            "unresolved_citations": result["unresolved_citations"],
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
