# 01: routing_mode + attempts schema, admission

**Status:** done (2026-10-09)

- [x] Migration: `research_runs.routing_mode`, `engine` nullable, `research_engine_attempts` table.
- [x] Admission: `routing_mode` in (auto, explicit); explicit requires a supported engine; auto takes no engine.
- [x] Chat service resolves routing from `research_options`; default auto.
