"""
tests/unit/test_structured_telemetry.py

Unit tests for structured telemetry, correlation ID propagation, and secret log sanitization:
- Propagation of workspace_id, conversation_id, turn_id, run_id, timeline_epoch in event payloads.
- Structured promotion decision audit logs with full correlation identifiers.
- Redaction of sensitive credentials, Bearer tokens, DB connection passwords, and JWTs.
"""

import json
import logging
from uuid import uuid4
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.telemetry import (
    sanitize_log_message,
    SecretSanitizingFilter,
    neosis_workspace_id,
    neosis_conversation_id,
    neosis_turn_id,
    neosis_run_id,
    neosis_timeline_epoch,
)
from app.services.chat.events import ChatEventRepository, ChatEventService
from app.models.research import ResearchArtifact
from app.services.research.promotion import PromotionService


def test_log_sanitizer_redacts_secrets():
    """
    Verifies that the log sanitizer strips authorization tokens, DB credentials,
    and secret API keys.
    """
    # 1. Bearer Token
    bearer_log = "Processing request with Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz.123"
    sanitized_bearer = sanitize_log_message(bearer_log)
    assert "Bearer [REDACTED]" in sanitized_bearer
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in sanitized_bearer

    # 2. Database Connection URL Password
    db_log = "Connecting to database at postgresql+asyncpg://app_user:super_secret_password_123@db.prod.internal:5432/prod_db"
    sanitized_db = sanitize_log_message(db_log)
    assert "app_user:[REDACTED]@db.prod.internal" in sanitized_db
    assert "super_secret_password_123" not in sanitized_db

    # 3. API Key and Secret Parameters
    api_log = "Invoking external LLM with api_key='sk-1234567890abcdef1234567890' and secret='top_secret_val_999'"
    sanitized_api = sanitize_log_message(api_log)
    assert '[REDACTED]' in sanitized_api
    assert "sk-1234567890abcdef1234567890" not in sanitized_api
    assert "top_secret_val_999" not in sanitized_api


def test_secret_sanitizing_filter_intercepts_log_records():
    """
    Verifies that SecretSanitizingFilter intercepts logging.LogRecord instances
    and redacts message strings and arguments.
    """
    filter_instance = SecretSanitizingFilter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="User session established with token Bearer secret_session_token_12345",
        args=(),
        exc_info=None,
    )

    filter_instance.filter(record)
    assert "secret_session_token_12345" not in record.msg
    assert "Bearer [REDACTED]" in record.msg

    # Test with format arguments
    record_with_args = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=12,
        msg="Database URL: %s",
        args=("postgresql+asyncpg://admin:pass123456@localhost:5432/db",),
        exc_info=None,
    )
    filter_instance.filter(record_with_args)
    assert "pass123456" not in record_with_args.args[0]
    assert "admin:[REDACTED]@" in record_with_args.args[0]


def test_correlation_context_vars():
    """
    Verifies that correlation context variables store and retrieve execution context correctly.
    """
    ws_id = str(uuid4())
    conv_id = str(uuid4())
    t_id = str(uuid4())
    r_id = str(uuid4())

    tok_ws = neosis_workspace_id.set(ws_id)
    tok_conv = neosis_conversation_id.set(conv_id)
    tok_turn = neosis_turn_id.set(t_id)
    tok_run = neosis_run_id.set(r_id)
    tok_epoch = neosis_timeline_epoch.set(4)

    try:
        assert neosis_workspace_id.get() == ws_id
        assert neosis_conversation_id.get() == conv_id
        assert neosis_turn_id.get() == t_id
        assert neosis_run_id.get() == r_id
        assert neosis_timeline_epoch.get() == 4
    finally:
        neosis_workspace_id.reset(tok_ws)
        neosis_conversation_id.reset(tok_conv)
        neosis_turn_id.reset(tok_turn)
        neosis_run_id.reset(tok_run)
        neosis_timeline_epoch.reset(tok_epoch)


@pytest.mark.asyncio
async def test_correlation_id_propagation_in_chat_events():
    """
    Verifies that ChatEventService.record_and_publish propagates standard correlation IDs
    in event payloads.
    """
    turn_id = uuid4()
    ws_id = uuid4()
    run_id = uuid4()

    mock_event = MagicMock()
    mock_event.event_id = uuid4()
    mock_event.sequence = 1
    mock_event.created_at = None

    mock_repo = MagicMock(spec=ChatEventRepository)
    mock_repo.append_event = AsyncMock(return_value=mock_event)
    mock_redis = AsyncMock()

    service = ChatEventService(mock_repo, mock_redis)

    payload = {
        "workspace_id": str(ws_id),
        "run_id": str(run_id),
        "turn_id": str(turn_id),
        "timeline_epoch": 2,
        "message": "Conducting deep search",
    }

    event = await service.record_and_publish(turn_id, "turn.researching", payload)

    mock_repo.append_event.assert_awaited_once_with(turn_id, "turn.researching", payload)
    mock_redis.publish.assert_awaited_once()

    published_data = json.loads(mock_redis.publish.await_args[0][1])
    assert published_data["event_type"] == "turn.researching"
    assert published_data["payload"]["workspace_id"] == str(ws_id)
    assert published_data["payload"]["run_id"] == str(run_id)
    assert published_data["payload"]["turn_id"] == str(turn_id)
    assert published_data["payload"]["timeline_epoch"] == 2


@pytest.mark.asyncio
async def test_correlation_id_in_promotion_decision_telemetry(caplog):
    """
    Verifies that candidate promotion decisions log structured telemetry with complete
    correlation identifiers (workspace_id, run_id, artifact_id, candidate_type, promotion_decision).
    """
    workspace_id = uuid4()
    artifact_id = uuid4()
    user_id = uuid4()
    run_id = uuid4()

    candidate = ResearchArtifact(
        artifact_id=artifact_id,
        run_id=run_id,
        type="memory_candidate",
        payload={"text": "Superconductor findings", "provenance": {}},
        promotion_status="pending_review",
    )

    session = AsyncMock()
    session.add = MagicMock()
    repo = MagicMock()
    repo.get_candidate_for_review = AsyncMock(return_value=candidate)

    derivation_svc = MagicMock()
    derivation_svc.validate_provenance_lineage = AsyncMock(return_value=True)

    promo_svc = PromotionService(
        session=session,
        research_repo=repo,
        derivation_service=derivation_svc,
        arq_pool=AsyncMock(),
    )

    with caplog.at_level(logging.INFO):
        await promo_svc.accept_candidate(workspace_id, artifact_id, user_id)

    # Inspect caplog for structured candidate_promotion_decision event
    decision_logs = [
        json.loads(record.message)
        for record in caplog.records
        if "candidate_promotion_decision" in record.message
    ]

    assert len(decision_logs) >= 1
    log_event = decision_logs[0]
    assert log_event["event"] == "candidate_promotion_decision"
    assert log_event["workspace_id"] == str(workspace_id)
    assert log_event["run_id"] == str(run_id)
    assert log_event["artifact_id"] == str(artifact_id)
    assert log_event["candidate_type"] == "memory_candidate"
    assert log_event["promotion_decision"] == "accepted"
    assert log_event["reviewed_by"] == str(user_id)
