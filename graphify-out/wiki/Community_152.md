# Community 152

> 20 nodes · cohesion 0.16

## Key Concepts

- **generate_unique_filename()** (9 connections) — `references/open-notebook/api/routers/sources.py`
- **test_upload_toctou_race.py** (9 connections) — `references/open-notebook/tests/test_upload_toctou_race.py`
- **TestFixedGenerateUniqueFilenameSurvivesRace** (6 connections) — `references/open-notebook/tests/test_upload_toctou_race.py`
- **.test_concurrent_uploads_to_same_name_all_survive()** (4 connections) — `references/open-notebook/tests/test_upload_toctou_race.py`
- **.test_concurrent_uploads_to_same_name_lose_data()** (4 connections) — `references/open-notebook/tests/test_upload_toctou_race.py`
- **distinct_payloads_on_disk()** (3 connections) — `references/open-notebook/tests/test_upload_toctou_race.py`
- **new_fixed_pattern()** (3 connections) — `references/open-notebook/tests/test_upload_toctou_race.py`
- **old_racy_pattern()** (3 connections) — `references/open-notebook/tests/test_upload_toctou_race.py`
- **run_concurrent_uploads()** (3 connections) — `references/open-notebook/tests/test_upload_toctou_race.py`
- **.test_claimed_path_exists_and_is_empty_immediately()** (3 connections) — `references/open-notebook/tests/test_upload_toctou_race.py`
- **.test_directory_components_are_stripped_not_traversed()** (3 connections) — `references/open-notebook/tests/test_upload_toctou_race.py`
- **TestOldPatternLosesWritesUnderRace** (3 connections) — `references/open-notebook/tests/test_upload_toctou_race.py`
- **.test_pre_existing_file_is_skipped()** (2 connections) — `references/open-notebook/tests/test_upload_toctou_race.py`
- **.test_sequential_calls_still_increment_correctly()** (2 connections) — `references/open-notebook/tests/test_upload_toctou_race.py`
- **Generate unique filename like Streamlit app (append counter if file exists),…** (1 connections) — `references/open-notebook/api/routers/sources.py`
- **Tests for the TOCTOU race fix in generate_unique_filename()…** (1 connections) — `references/open-notebook/tests/test_upload_toctou_race.py`
- **os.path.basename() strips directory components from the original filename…** (1 connections) — `references/open-notebook/tests/test_upload_toctou_race.py`
- **Standalone repro of the pre-fix check-then-act pattern, with an injected delay…** (1 connections) — `references/open-notebook/tests/test_upload_toctou_race.py`
- **Confirms the vulnerability this fix addresses is real, using a standalone repro…** (1 connections) — `references/open-notebook/tests/test_upload_toctou_race.py`
- **The function itself must create the file (not just check for its absence) -…** (1 connections) — `references/open-notebook/tests/test_upload_toctou_race.py`

## Relationships

- [Community 1](Community_1.md) (3 shared connections)

## Source Files

- `references/open-notebook/api/routers/sources.py`
- `references/open-notebook/tests/test_upload_toctou_race.py`

## Audit Trail

- EXTRACTED: 31 (94%)
- INFERRED: 2 (6%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*