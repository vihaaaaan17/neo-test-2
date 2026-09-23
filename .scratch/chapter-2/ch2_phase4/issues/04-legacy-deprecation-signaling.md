# 04: Legacy Ground Deprecation Signaling

**What to build:** Annotates the legacy `GroundModeOrchestrator` with `@deprecated`, emits a `logger.warning` on instantiation, and fires a non-blocking `legacy_ground_engine_instantiated` telemetry metric. Includes routing tests proving the legacy engine is *not* selected during the default `OPEN_NOTEBOOK_ENABLED=True` path.

**Blocked by:** 03 (The cutover router must be in place to verify the fallback path)

**Status:** ready-for-agent

- [ ] Add `@deprecated` to `GroundModeOrchestrator` class in `app/orchestration/ground_mode.py`.
- [ ] Add `logger.warning("GroundModeOrchestrator is deprecated...")` to `__init__`.
- [ ] Emit a non-blocking telemetry event metric `legacy_ground_engine_instantiated` from `__init__`.
- [ ] Add a test verifying that when `OPEN_NOTEBOOK_ENABLED=True`, the legacy engine is not instantiated (no metric or warning fired).
- [ ] Add a test verifying that when `OPEN_NOTEBOOK_ENABLED=False`, the legacy engine is instantiated correctly without failing.
