# 02: Turn + Event Concurrency

**What to build:**
Fix turn submission, concurrency control, and event emission authority in the existing Chapter 4 implementation. Validate turn `mode` and parameters *before* allocating sequence numbers or persisting turns to PostgreSQL, rejecting bad inputs immediately with zero pending turn rows created. In `submit_turn()`, row-lock the conversation (`SELECT ... FOR UPDATE`) and enforce the one-running-turn invariant by rejecting submissions with `HTTP 409 conversation_turn_in_progress` if an active turn is pending or running. Make the ARQ background worker the single authoritative writer of `ChatEvent` rows in PostgreSQL and publisher to Redis `turn_events:{turn_id}`, removing duplicate bridge event emissions in `ChatService`. Use atomic Compare-And-Swap (CAS) queries (`UPDATE conversation_turns SET status = :target WHERE turn_id = :id AND status IN ('pending', 'running')`) for both turn completion and cancellation handlers to guarantee that cancellation and worker completion races resolve deterministically to exactly one immutable terminal status.

**Blocked by:** 01: Ground + Streaming Fabric

**Status:** completed

- [x] Invalid turn modes and parameters fail validation immediately with zero unexecuted rows persisted to `conversation_turns`.
- [x] Submitting a second turn while an existing turn is pending or running fails with `HTTP 409 conversation_turn_in_progress`.
- [x] ARQ background worker is the sole creator of research `ChatEvent`s; API process only streams and replays them with zero duplicate records.
- [x] Turn cancellation and completion races resolve to exactly one immutable terminal status via atomic CAS updates.
- [x] Canonical event type constants are unified across models, repositories, emitters, and the event catalog.
