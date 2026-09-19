# Community 174

> 18 nodes · cohesion 0.15

## Key Concepts

- **AsyncMigrationManager** (31 connections) — `references/open-notebook/open_notebook/database/async_migrate.py`
- **.get_current_version()** (6 connections) — `references/open-notebook/open_notebook/database/async_migrate.py`
- **TestMigration20** (6 connections) — `references/open-notebook/tests/test_podcast_speaker_profile.py`
- **TestMigration22Registration** (5 connections) — `references/open-notebook/tests/test_podcast_legacy_field_removal.py`
- **.needs_migration()** (4 connections) — `references/open-notebook/open_notebook/database/async_migrate.py`
- **.ping()** (4 connections) — `references/open-notebook/open_notebook/database/async_migrate.py`
- **.run_migration_up()** (4 connections) — `references/open-notebook/open_notebook/database/async_migrate.py`
- **.test_manager_registers_migration_22()** (2 connections) — `references/open-notebook/tests/test_podcast_legacy_field_removal.py`
- **.test_migration_is_registered_in_manager()** (2 connections) — `references/open-notebook/tests/test_podcast_speaker_profile.py`
- **Get current database version.** (1 connections) — `references/open-notebook/open_notebook/database/async_migrate.py`
- **Check whether SurrealDB is reachable for migration startup.** (1 connections) — `references/open-notebook/open_notebook/database/async_migrate.py`
- **Check if migration is needed.** (1 connections) — `references/open-notebook/open_notebook/database/async_migrate.py`
- **Main migration manager with async support.** (1 connections) — `references/open-notebook/open_notebook/database/async_migrate.py`
- **Migration files exist and are registered in AsyncMigrationManager (migrations…** (1 connections) — `references/open-notebook/tests/test_podcast_legacy_field_removal.py`
- **.test_migration_files_exist()** (1 connections) — `references/open-notebook/tests/test_podcast_legacy_field_removal.py`
- **Migration 20 converts speaker_config from name string to record link.…** (1 connections) — `references/open-notebook/tests/test_podcast_speaker_profile.py`
- **.test_migration_converts_names_and_tightens_type()** (1 connections) — `references/open-notebook/tests/test_podcast_speaker_profile.py`
- **.test_migration_down_restores_names()** (1 connections) — `references/open-notebook/tests/test_podcast_speaker_profile.py`

## Relationships

- [Community 237](Community_237.md) (3 shared connections)
- [Community 260](Community_260.md) (3 shared connections)
- [Community 167](Community_167.md) (3 shared connections)
- [Community 172](Community_172.md) (2 shared connections)
- [Community 296](Community_296.md) (2 shared connections)
- [Community 312](Community_312.md) (2 shared connections)
- [Community 297](Community_297.md) (2 shared connections)
- [Community 221](Community_221.md) (2 shared connections)
- [Community 109](Community_109.md) (2 shared connections)
- [Community 1](Community_1.md) (1 shared connections)
- [Community 251](Community_251.md) (1 shared connections)
- [Community 85](Community_85.md) (1 shared connections)

## Source Files

- `references/open-notebook/open_notebook/database/async_migrate.py`
- `references/open-notebook/tests/test_podcast_legacy_field_removal.py`
- `references/open-notebook/tests/test_podcast_speaker_profile.py`

## Audit Trail

- EXTRACTED: 41 (82%)
- INFERRED: 9 (18%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*