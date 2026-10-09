# ADR 0002: Formal Deferral of STORM Integration to Chapter 5

## Status
**Superseded by [ADR 0006](0006-storm-and-gpt-researcher-as-selectable-engines.md)** (2026-10-08) Its load-test condition is now the
separate *validated for production workload* state (not yet met). Its governance concerns are addressed for automatic routing by
[ADR 0007](0007-conversational-turns-and-engine-routing.md): sequential single-engine turns, a shared turn budget, bounded
upstream profiles and concurrency slots. Originally: Deferred (Effective Date: September 22, 2026)

## Context
During the Chapter 3 Research Engine architecture design and implementation, Knowledge STORM (Synthesis and Topic Oriented Research Manager) was evaluated as a potential capability for perspective generation, multi-perspective question decomposition, and outline scaffolding. 

However, introducing STORM as an autonomous research supervisor alongside Open Deep Research (ODR) presents significant architectural risks:
1. **Supervisory Duplication:** ODR already provides comprehensive graph-based planning, agent task distribution, and recursive research loops. Adding STORM as a second independent supervisor would violate the single-supervisor architectural contract.
2. **Resource Governance & Scalability:** Under our 1,000-user production scaling target, managing concurrent dual-supervisor workflows introduces unpredictable token usage, unbounded fan-out, and memory pressure.
3. **Evidence & Provenance Integrity:** STORM's upstream state management does not natively conform to Neosis's strict workspace-isolated `ResearchEvidence`, fingerprinting, and normalization ACL pipeline.

## Decision
We formally **defer STORM integration to Chapter 5** (Evaluation & Advanced Reliability). 
- Open Deep Research (ODR) remains the sole primary research execution runtime.
- GPT Researcher is integrated strictly as a capability retriever via the Neosis ACL (Ticket 09).
- STORM capabilities (such as perspective-based question decomposition) will be evaluated in Chapter 5 only after ODR production hardening, load testing, and database/checkpoint durability are fully verified under 1,000-user load.

## Consequences
- **Positive:** Reduces architectural drift, maintains a single clean research execution plane, preserves strict provenance and resource governance, and avoids unnecessary multi-supervisor complexity during initial scaling passes.
- **Negative / Trade-off:** Multi-perspective outline generation will temporarily rely on ODR's built-in subtopic planning rather than dedicated STORM tree synthesis.
- **Configuration:** A explicit feature flag `STORM_ENABLED: bool = False` has been added to `Settings` in `app/core/config.py` to ensure fail-closed governance.
