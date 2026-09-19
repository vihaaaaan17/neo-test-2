# Community 202

> 14 nodes · cohesion 0.16

## Key Concepts

- **app/main.py** (18 connections) — `app/main.py`
- **rate_limit.py** (3 connections) — `app/api/deps/rate_limit.py`
- **get_rate_limit_key()** (3 connections) — `app/api/deps/rate_limit.py`
- **health_check()** (3 connections) — `app/main.py`
- **telemetry.py** (2 connections) — `app/core/telemetry.py`
- **setup_telemetry()** (2 connections) — `app/core/telemetry.py`
- **lifespan()** (2 connections) — `app/main.py`
- **FastAPI** (2 connections)
- **test_health.py** (2 connections) — `tests/test_health.py`
- **test_health_check()** (2 connections) — `tests/test_health.py`
- **Request** (1 connections)
- **Rate limit by user ID if authenticated, else fallback to IP.** (1 connections) — `app/api/deps/rate_limit.py`
- **get** (1 connections)
- **Deep health check verifying Postgres and Neo4j connectivity.** (1 connections) — `app/main.py`

## Relationships

- [Community 21](Community_21.md) (4 shared connections)
- [Community 43](Community_43.md) (2 shared connections)
- [Community 34](Community_34.md) (2 shared connections)
- [Community 50](Community_50.md) (2 shared connections)
- [Community 37](Community_37.md) (1 shared connections)
- [Community 60](Community_60.md) (1 shared connections)
- [Community 15](Community_15.md) (1 shared connections)

## Source Files

- `app/api/deps/rate_limit.py`
- `app/core/telemetry.py`
- `app/main.py`
- `tests/test_health.py`

## Audit Trail

- EXTRACTED: 27 (96%)
- INFERRED: 1 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*