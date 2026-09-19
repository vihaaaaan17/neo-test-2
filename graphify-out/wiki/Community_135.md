# Community 135

> 22 nodes · cohesion 0.15

## Key Concepts

- **QuotaService** (25 connections) — `app/services/quota.py`
- **test_quota.py** (10 connections) — `tests/test_quota.py`
- **asyncio** (6 connections)
- **get_quota_service()** (5 connections) — `app/services/quota.py`
- **UUID** (5 connections)
- **.check_knowledge_limit()** (4 connections) — `app/services/quota.py`
- **.check_source_limit()** (4 connections) — `app/services/quota.py`
- **.check_storage_limit()** (4 connections) — `app/services/quota.py`
- **.check_workspace_limit()** (4 connections) — `app/services/quota.py`
- **test_check_knowledge_limit_fail()** (3 connections) — `tests/test_quota.py`
- **test_check_source_limit_fail()** (3 connections) — `tests/test_quota.py`
- **test_check_storage_limit_fail()** (3 connections) — `tests/test_quota.py`
- **test_check_workspace_limit_fail()** (3 connections) — `tests/test_quota.py`
- **test_check_workspace_limit_pass()** (3 connections) — `tests/test_quota.py`
- **AsyncSession** (2 connections)
- **.__init__()** (2 connections) — `app/services/quota.py`
- **mock_db()** (2 connections) — `tests/test_quota.py`
- **Check if user has exceeded their workspace limit.** (1 connections) — `app/services/quota.py`
- **Check if workspace has exceeded its source count limit.** (1 connections) — `app/services/quota.py`
- **Check if workspace has exceeded its total storage limit.** (1 connections) — `app/services/quota.py`
- **Check if workspace has exceeded its knowledge memory limit.** (1 connections) — `app/services/quota.py`
- **fixture** (1 connections)

## Relationships

- [Community 34](Community_34.md) (9 shared connections)
- [Community 43](Community_43.md) (5 shared connections)
- [Community 24](Community_24.md) (4 shared connections)
- [Community 64](Community_64.md) (3 shared connections)
- [Community 21](Community_21.md) (2 shared connections)

## Source Files

- `app/services/quota.py`
- `tests/test_quota.py`

## Audit Trail

- EXTRACTED: 40 (69%)
- INFERRED: 18 (31%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*