# Community 113

> 27 nodes · cohesion 0.09

## Key Concepts

- **GlobalRateLimiter** (13 connections) — `references/gpt-researcher/gpt_researcher/utils/rate_limiter.py`
- **get_global_rate_limiter()** (6 connections) — `references/gpt-researcher/gpt_researcher/utils/rate_limiter.py`
- **test_rate_limiter_configure.py** (5 connections) — `references/gpt-researcher/tests/test_rate_limiter_configure.py`
- **rate_limiter.py** (4 connections) — `references/gpt-researcher/gpt_researcher/utils/rate_limiter.py`
- **.configure()** (3 connections) — `references/gpt-researcher/gpt_researcher/utils/rate_limiter.py`
- **.get_lock()** (3 connections) — `references/gpt-researcher/gpt_researcher/utils/rate_limiter.py`
- **.wait_if_needed()** (3 connections) — `references/gpt-researcher/gpt_researcher/utils/rate_limiter.py`
- **.__init__()** (3 connections) — `references/gpt-researcher/gpt_researcher/utils/workers.py`
- **.throttle()** (3 connections) — `references/gpt-researcher/gpt_researcher/utils/workers.py`
- **.__init__()** (2 connections) — `references/gpt-researcher/gpt_researcher/utils/rate_limiter.py`
- **.reset()** (2 connections) — `references/gpt-researcher/gpt_researcher/utils/rate_limiter.py`
- **test_configure_coerces_string_delay()** (2 connections) — `references/gpt-researcher/tests/test_rate_limiter_configure.py`
- **test_configure_none_is_zero()** (2 connections) — `references/gpt-researcher/tests/test_rate_limiter_configure.py`
- **test_configure_rejects_garbage()** (2 connections) — `references/gpt-researcher/tests/test_rate_limiter_configure.py`
- **test_configure_rejects_negative()** (2 connections) — `references/gpt-researcher/tests/test_rate_limiter_configure.py`
- **.__new__()** (1 connections) — `references/gpt-researcher/gpt_researcher/utils/rate_limiter.py`
- **Global rate limiter for scraper requests. Ensures that SCRAPER_RATE_LIMIT_DELAY…** (1 connections) — `references/gpt-researcher/gpt_researcher/utils/rate_limiter.py`
- **Get the global rate limiter singleton instance.** (1 connections) — `references/gpt-researcher/gpt_researcher/utils/rate_limiter.py`
- **Singleton global rate limiter. Ensures minimum delay between ANY scraper…** (1 connections) — `references/gpt-researcher/gpt_researcher/utils/rate_limiter.py`
- **Initialize the global rate limiter (only once).** (1 connections) — `references/gpt-researcher/gpt_researcher/utils/rate_limiter.py`
- **Get or create the async lock (must be called from async context).** (1 connections) — `references/gpt-researcher/gpt_researcher/utils/rate_limiter.py`
- **Configure the global rate limit delay. Args: rate_limit_delay: Minimum seconds…** (1 connections) — `references/gpt-researcher/gpt_researcher/utils/rate_limiter.py`
- **Wait if needed to enforce global rate limiting. This method ensures that…** (1 connections) — `references/gpt-researcher/gpt_researcher/utils/rate_limiter.py`
- **Reset the rate limiter state (useful for testing).** (1 connections) — `references/gpt-researcher/gpt_researcher/utils/rate_limiter.py`
- **Initialize WorkerPool with concurrency and rate limiting. Args: max_workers:…** (1 connections) — `references/gpt-researcher/gpt_researcher/utils/workers.py`
- *... and 2 more nodes in this community*

## Relationships

- [Community 48](Community_48.md) (4 shared connections)
- [Community 109](Community_109.md) (1 shared connections)

## Source Files

- `references/gpt-researcher/gpt_researcher/utils/rate_limiter.py`
- `references/gpt-researcher/gpt_researcher/utils/workers.py`
- `references/gpt-researcher/tests/test_rate_limiter_configure.py`

## Audit Trail

- EXTRACTED: 31 (86%)
- INFERRED: 5 (14%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*