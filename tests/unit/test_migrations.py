"""
tests/unit/test_migrations.py

Unit tests for Alembic migration integrity, DAG linearity, upgrade/downgrade completeness,
foreign key cascades, table primary keys, and index coverage across all Chapter 4 models.
"""

import os
import pytest
from scripts.validate_migrations import audit_dag_linearity, audit_schema_models, parse_revision_ast
from app.core.database import Base
import app.models  # noqa: F401


@pytest.fixture(scope="module")
def versions_dir():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(repo_root, "alembic", "versions")


def test_migration_dag_linearity_and_single_head(versions_dir):
    """
    Asserts all 22 Alembic revisions form a strictly linear DAG with a single root and single head.
    """
    audit = audit_dag_linearity(versions_dir)
    assert audit["total_revisions"] == 22
    assert audit["root"] == "f23c3a900272"
    assert audit["head"] == "7a3e9c5d1f68"
    assert len(audit["ordered_chain"]) == 22
    assert audit["ordered_chain"][0] == audit["root"]
    assert audit["ordered_chain"][-1] == audit["head"]


def test_all_revisions_contain_upgrade_and_downgrade(versions_dir):
    """
    Every revision script must define non-empty upgrade() and downgrade() functions.
    """
    audit = audit_dag_linearity(versions_dir)
    for rev_id, data in audit["revisions"].items():
        assert data["has_upgrade"] is True, f"Revision {rev_id} ({data['file']}) missing non-empty upgrade()"
        assert data["has_downgrade"] is True, f"Revision {rev_id} ({data['file']}) missing non-empty downgrade()"


def test_schema_models_comprehensive_audit():
    """
    Validates that all required Chapter 4 tables, primary keys, foreign keys, and indexes are present.
    """
    result = audit_schema_models()
    assert result["total_tables"] >= 18
    assert result["required_tables_verified"] == 17
    assert result["fk_checks_verified"] == 10
    assert result["index_checks_verified"] == 6


def test_critical_foreign_key_cascades():
    """
    Verifies that cascade and set-null rules on critical foreign keys strictly adhere to data lifecycle specs:
    - Child entities of conversations cascade on deletion.
    - Research runs preserve historical records with SET NULL when parent conversation is deleted.
    """
    tables = Base.metadata.tables

    # 1. conversations.workspace_id -> CASCADE
    conv_ws_fk = list(tables["conversations"].columns["workspace_id"].foreign_keys)[0]
    assert conv_ws_fk.ondelete == "CASCADE"

    # 2. conversation_turns.conversation_id -> CASCADE
    turn_conv_fk = list(tables["conversation_turns"].columns["conversation_id"].foreign_keys)[0]
    assert turn_conv_fk.ondelete == "CASCADE"

    # 3. chat_events.turn_id -> CASCADE
    event_turn_fk = list(tables["chat_events"].columns["turn_id"].foreign_keys)[0]
    assert event_turn_fk.ondelete == "CASCADE"

    # 4. research_runs.conversation_id -> SET NULL (historical research preserved)
    run_conv_fk = list(tables["research_runs"].columns["conversation_id"].foreign_keys)[0]
    assert run_conv_fk.ondelete == "SET NULL"

    # 5. research_runs.turn_id -> SET NULL (historical research preserved)
    run_turn_fk = list(tables["research_runs"].columns["turn_id"].foreign_keys)[0]
    assert run_turn_fk.ondelete == "SET NULL"

    # 6. open_notebook_conversation_bindings.conversation_id -> CASCADE
    binding_conv_fk = list(tables["open_notebook_conversation_bindings"].columns["conversation_id"].foreign_keys)[0]
    assert binding_conv_fk.ondelete == "CASCADE"


def test_core_column_nullability_and_defaults():
    """
    Verifies that invariants on column nullability and defaults are preserved across all core models.
    """
    tables = Base.metadata.tables

    # Workspace timeline epoch
    ws_tbl = tables["workspaces"]
    assert ws_tbl.columns["timeline_epoch"].nullable is False
    assert ws_tbl.columns["status"].nullable is False

    # Canonical conversations
    conv_tbl = tables["conversations"]
    assert conv_tbl.columns["conversation_id"].primary_key is True
    assert conv_tbl.columns["workspace_id"].nullable is False
    assert conv_tbl.columns["owner_id"].nullable is False
    assert conv_tbl.columns["status"].nullable is False
    assert conv_tbl.columns["last_turn_sequence"].nullable is False

    # Conversation turns
    turn_tbl = tables["conversation_turns"]
    assert turn_tbl.columns["turn_id"].primary_key is True
    assert turn_tbl.columns["conversation_id"].nullable is False
    assert turn_tbl.columns["sequence"].nullable is False
    assert turn_tbl.columns["mode"].nullable is False
    assert turn_tbl.columns["status"].nullable is False

    # Chat events
    event_tbl = tables["chat_events"]
    assert event_tbl.columns["event_id"].primary_key is True
    assert event_tbl.columns["turn_id"].nullable is False
    assert event_tbl.columns["sequence"].nullable is False
    assert event_tbl.columns["event_type"].nullable is False

    # Research artifacts
    art_tbl = tables["research_artifacts"]
    assert art_tbl.columns["artifact_id"].primary_key is True
    # Run-scoped OR study-session-scoped (Chapter 6); a check constraint requires one of the two anchors.
    assert art_tbl.columns["run_id"].nullable is True
    assert art_tbl.columns["workspace_id"].nullable is True and art_tbl.columns["conversation_id"].nullable is True
    assert art_tbl.columns["type"].nullable is False
    assert art_tbl.columns["promotion_status"].nullable is False
