import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from fastapi import Response

from app.api.routes.research import create_research_run
from app.models.research import ResearchRun
from app.models.conversation import Conversation, ConversationTurn


@pytest.mark.asyncio
async def test_legacy_research_route_auto_creates_conversation():
    """
    When POST /research is invoked without conversation_id, it should:
    1. Auto-create a canonical Conversation titled 'Research: ...'
    2. Submit a turn with mode='research' via ChatService
    3. Set RFC 8288 Deprecation headers
    4. Return the resulting ResearchRun
    """
    workspace_id = uuid4()
    user_id = uuid4()
    run_id = uuid4()
    conv_id = uuid4()
    turn_id = uuid4()

    mock_user = MagicMock()
    mock_user.id = user_id

    mock_conv = Conversation(
        conversation_id=conv_id,
        workspace_id=workspace_id,
        owner_id=user_id,
        title="Research: Quantum battery..."
    )
    mock_turn = ConversationTurn(
        turn_id=turn_id,
        conversation_id=conv_id,
        workspace_id=workspace_id,
        owner_id=user_id,
        sequence=1,
        mode="research",
        research_run_id=run_id
    )
    mock_run = ResearchRun(
        run_id=run_id,
        workspace_id=workspace_id,
        owner_id=user_id,
        objective="Quantum battery",
        engine="open_deep_research"
    )

    mock_session = AsyncMock()
    mock_redis = AsyncMock()
    response = Response()

    with patch("app.api.routes.research.ConversationRepository") as mock_conv_repo_cls, \
         patch("app.api.routes.research.ChatService") as mock_chat_service_cls, \
         patch("app.api.routes.research.ResearchRepository") as mock_research_repo_cls:

        mock_conv_repo = mock_conv_repo_cls.return_value
        mock_conv_repo.create_conversation = AsyncMock(return_value=mock_conv)

        mock_chat_service = mock_chat_service_cls.return_value
        mock_chat_service.submit_turn = AsyncMock(return_value=mock_turn)

        mock_research_repo = mock_research_repo_cls.return_value
        mock_research_repo.get_run = AsyncMock(return_value=mock_run)

        result = await create_research_run(
            workspace_id=workspace_id,
            objective="Quantum battery",
            engine="open_deep_research",
            engine_revision=None,
            conversation_id=None,
            response=response,
            current_user=mock_user,
            session=mock_session,
            redis_client=mock_redis
        )

        assert result.run_id == run_id
        # Verify conversation creation
        mock_conv_repo.create_conversation.assert_awaited_once()
        # Verify submit_turn called with mode='research'
        mock_chat_service.submit_turn.assert_awaited_once()
        call_kwargs = mock_chat_service.submit_turn.call_args.kwargs
        assert call_kwargs["workspace_id"] == workspace_id
        assert call_kwargs["conversation_id"] == conv_id
        assert call_kwargs["turn_create"].mode == "research"
        assert call_kwargs["turn_create"].message == "Quantum battery"

        # Verify Deprecation headers
        assert response.headers["Deprecation"] == "true"
        assert "rel=\"successor-version\"" in response.headers["Link"]


@pytest.mark.asyncio
async def test_legacy_research_route_uses_provided_conversation():
    """
    When POST /research is invoked with an explicit conversation_id,
    it verifies ownership and appends the turn to that existing conversation.
    """
    workspace_id = uuid4()
    user_id = uuid4()
    run_id = uuid4()
    conv_id = uuid4()
    turn_id = uuid4()

    mock_user = MagicMock()
    mock_user.id = user_id

    mock_conv = Conversation(
        conversation_id=conv_id,
        workspace_id=workspace_id,
        owner_id=user_id,
        title="Existing Inquiry"
    )
    mock_turn = ConversationTurn(
        turn_id=turn_id,
        conversation_id=conv_id,
        workspace_id=workspace_id,
        owner_id=user_id,
        sequence=2,
        mode="research",
        research_run_id=run_id
    )
    mock_run = ResearchRun(
        run_id=run_id,
        workspace_id=workspace_id,
        owner_id=user_id,
        objective="Follow up search",
        engine="open_deep_research"
    )

    mock_session = AsyncMock()
    mock_redis = AsyncMock()
    response = Response()

    with patch("app.api.routes.research.ConversationRepository") as mock_conv_repo_cls, \
         patch("app.api.routes.research.ChatService") as mock_chat_service_cls, \
         patch("app.api.routes.research.ResearchRepository") as mock_research_repo_cls:

        mock_conv_repo = mock_conv_repo_cls.return_value
        mock_conv_repo.get_conversation = AsyncMock(return_value=mock_conv)

        mock_chat_service = mock_chat_service_cls.return_value
        mock_chat_service.submit_turn = AsyncMock(return_value=mock_turn)

        mock_research_repo = mock_research_repo_cls.return_value
        mock_research_repo.get_run = AsyncMock(return_value=mock_run)

        result = await create_research_run(
            workspace_id=workspace_id,
            objective="Follow up search",
            engine="open_deep_research",
            engine_revision=None,
            conversation_id=conv_id,
            response=response,
            current_user=mock_user,
            session=mock_session,
            redis_client=mock_redis
        )

        assert result.run_id == run_id
        # Must verify existing conversation
        mock_conv_repo.get_conversation.assert_awaited_once_with(workspace_id, conv_id)
        # Must NOT create a new conversation
        assert not hasattr(mock_conv_repo, "create_conversation") or not mock_conv_repo.create_conversation.called
        # Verify turn submitted
        mock_chat_service.submit_turn.assert_awaited_once()
        assert response.headers["Deprecation"] == "true"
