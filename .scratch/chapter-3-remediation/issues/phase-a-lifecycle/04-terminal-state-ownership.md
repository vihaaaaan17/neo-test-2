# 04: Terminal State Ownership

**What to build:** Modifies tasks.py and the ResearchEngine adapter interface so only ResearchLifecycleService governs terminal state transitions, preventing async workers from blindly overwriting PARTIAL or FAILED runs with COMPLETED.

**Blocked by:** 03: Error Classification & Fallback Removal

**Status:** ready-for-agent

- [ ] Acceptance criterion 1
- [ ] Acceptance criterion 2
