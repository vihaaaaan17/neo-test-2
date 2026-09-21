# 01: Phase 2 Canonical Models & Migrations

**What to build:** 
Expand the canonical domain models in `app/models/research.py` to establish the full Phase 2 research fabric, bringing it out of a prototype state into a durable system of record. Generate the Alembic migration to safely create the tables without impacting existing features.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [x] Add `ResearchEvidence` model with a nullable `source_id` foreign key, retrieving details (content, fingerprint), and tagging fields.
- [x] Add `ResearchArtifact` model with explicit types (e.g., `memory_candidate`, `graph_candidate`) and JSONB payload.
- [x] Add `ResearchReport` model for finalized synthesized reports.
- [x] Add `ResearchUsage` model for run/task accounting (tokens, latency, cost).
- [x] Add `ResearchEvent` model to capture canonical audit events.
- [x] Generate Alembic migration applying these models safely to the database.
