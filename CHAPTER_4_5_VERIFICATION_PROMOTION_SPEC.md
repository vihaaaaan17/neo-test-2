# Chapter 4.5 — Verification, Critique, Derivation & Human-Controlled Promotion

## 1. Purpose

Chapter 4.5 is a focused backend quality and governance layer on top of the Chapter 4 memory/state architecture.

It does not introduce a new research engine, supervisor, retriever architecture, Ground architecture, worker architecture, or storage architecture.

Its purpose is to answer: when Research produces a claim, finding, hypothesis, memory candidate, or graph candidate, how does Neosis determine whether it is sufficiently supported, expose uncertainty and contradiction, and obtain explicit user approval before making the result durable?

Primary flow:

`Research → evidence → claims/findings → verification/critique → candidate → user review → accept/reject → durable promotion`

Ground remains source-grounded. Research-derived knowledge and derived graph entities never become Ground evidence merely because they were promoted.

## 2. Existing Repository Baseline

Chapter 4.5 builds on the current repository.

Relevant existing components:

- `app/services/research/provenance.py` — citation/provenance audit; currently verifies referential integrity between report citations and `ResearchEvidence`, but does not establish semantic entailment/support.
- `app/services/research/service.py` — currently promotes `memory_candidate` artifacts into `KnowledgeMemory` and `graph_candidate` artifacts into the Output KG.
- `app/models/research.py` — `ResearchRun`, `ResearchTask`, `ResearchEvidence`, `ResearchArtifact`, `ResearchReport`, `ResearchUsage`, `ResearchEvent`.
- `app/models/knowledge.py` — `KnowledgeMemory`.
- `app/schemas/knowledge.py` — `Provenance`, `KnowledgeMemoryCreate`.
- `app/schemas/graph.py` — `ProvenanceBundle`, `OutputGraphNode`, `OutputGraphEdge`, `OutputGraph`.
- `app/repositories/graph.py` — Output KG projection and retrieval with persisted provenance.
- `app/workers/tasks.py` — current research completion path reaches automatic promotion; this becomes the main integration boundary for human-controlled promotion.

Chapter 3 remediation remains an input to this chapter, not a redesign target.

## 3. Non-Goals

Do not use Chapter 4.5 to:

- redesign ODR
- introduce a new research supervisor
- implement STORM
- redesign retrievers
- rewrite Open Notebook
- redesign Redis/ARQ
- replace PostgreSQL
- introduce another canonical graph database
- build a new ResearchEngine
- make KnowledgeMemory a Ground retrieval source
- automatically inject derived memory into Ground
- build the Chapter 5 frontend

## 4. Core Invariants

### 4.1 Ground evidence isolation

Ground evidence remains:

`canonical uploaded/selected source → Open Notebook → grounded answer`

Research-derived KnowledgeMemory, Output KG nodes, hypotheses, reports, and derived claims are not Ground evidence.

Ground may receive contextual state needed to interpret a request, but its factual answer must still be grounded in the canonical source corpus.

### 4.2 Research results are not automatically trusted

Research output first exists as candidate material.

Candidate lifecycle should distinguish at least:

- `candidate`
- `under_review`
- `accepted`
- `rejected`
- `superseded`

Only accepted candidates may cross the durable promotion boundary.

### 4.3 Evidence is different from claims

An evidence record is not a claim. Claims reference evidence. Derived findings reference evidence/claims plus a derivation record where applicable.

### 4.4 Deterministic verification outranks LLM self-approval

Where a result can be verified deterministically, deterministic verification is preferred: arithmetic, unit conversions, formula evaluation, schema validation, source existence, and provenance integrity.

An LLM may propose or explain a derivation, but should not be the sole authority for a deterministic calculation.

### 4.5 User approval is the final durable boundary

The system may automatically identify candidates, verify evidence, detect contradictions, estimate confidence, and prepare promotion proposals. It must not silently make candidates durable under the normal review policy.

## 5. Verification Model

### Layer A — Referential verification

Retain the existing chain:

`Report → Citation → ResearchEvidence → ResearchRun → Workspace`

### Layer B — Source resolution

Where possible, resolve external citations to canonical `Source` or `SourceSnapshot` records. Unresolved external evidence remains explicitly unresolved.

### Layer C — Semantic support verification

For each claim:

`claim + supporting evidence → semantic verifier`

The verifier should classify evidence as supporting, partially supporting, contradicting, unrelated, or insufficient.

Persist at minimum:

- verifier type
- model/revision
- evidence references
- verdict
- confidence
- timestamp
- verification version

The verifier itself is not evidence.

### Layer D — Derivation verification

For derived claims:

`inputs → derivation expression → deterministic verification`

Persist:

- input references
- expression/operation
- normalized values where needed
- calculated output
- verification method
- result
- verifier revision

Example:

`(1.42 / 1.20 - 1) × 100 = 18.3%`

must be represented as structured derivation metadata, not only prose.

### Layer E — Cross-evidence contradiction detection

Identify when distinct evidence items imply incompatible claims.

A contradiction record should identify:

- claim A
- claim B
- evidence for A
- evidence for B
- contradiction type
- confidence
- explicit vs inferred classification

Contradiction is a quality/uncertainty signal, not automatically a system error.

## 6. Critic Pass

Research results should optionally pass through a dedicated critique stage after synthesis and before promotion.

The critic should check:

- unsupported claims
- over-generalization
- weak evidence chains
- contradictory evidence
- missing evidence
- confidence exceeding evidence quality
- calculations lacking adequate inputs
- unresolved citations

The critic emits structured findings and does not directly mutate durable memory.

Example:

```json
{
  "claim_id": "claim-42",
  "issue_type": "unsupported_generalization",
  "severity": "medium",
  "evidence_refs": ["evidence-1", "evidence-7"],
  "recommended_action": "narrow_claim"
}
```

## 7. Candidate and Promotion Model

The existing `ResearchArtifact` system is the correct starting point.

Replace:

`ResearchArtifact → automatic promotion`

with:

`ResearchArtifact → promotion candidate → review → decision → promotion`

A candidate should contain:

- candidate ID
- workspace ID
- run ID
- artifact ID
- candidate type
- proposed content
- evidence references
- provenance
- derivation metadata
- verification results
- contradiction flags
- confidence
- status
- timestamps

Candidate types should include at minimum:

- memory candidate
- graph candidate
- finding candidate
- hypothesis candidate

## 8. Human Review Contract

The backend must support explicit `accept` and `reject` decisions.

Persist:

- reviewer identity
- decision
- timestamp
- optional reason/comment
- candidate version
- verification snapshot used for the decision

A rejected candidate remains historically visible and auditable and must not later be silently promoted.

An accepted candidate becomes eligible for the appropriate promotion path.

Promotion must be idempotent.

## 9. Promotion Paths

### Memory promotion

`candidate → accepted → KnowledgeMemory`

Preserve research provenance, evidence references, verification state, originating run, and candidate identity.

Promoted research memory remains explicitly research-derived and is excluded from Ground evidence.

### Output KG promotion

`candidate → accepted → OutputGraph → Neo4j`

Output nodes/edges should retain derivation provenance, evidence references, calculation, verification status, originating research run, and candidate identity.

The Output KG is a user-visible research artifact, not the Ground source corpus.

## 10. Data Model Direction

Prefer extending existing models rather than creating parallel systems.

Likely additions belong around `ResearchArtifact`, `KnowledgeMemory`, and provenance structures, plus a dedicated review/promotion record where immutable audit history is needed.

Conceptual model:

```text
ResearchArtifact
    |
    v
PromotionCandidate
    |
    +--> VerificationResult[]
    |
    +--> CritiqueResult[]
    |
    +--> ContradictionResult[]
    |
    v
PromotionDecision
    |
    +--> accepted --> KnowledgeMemory
    |
    +--> accepted --> Output KG
    |
    +--> rejected
```

Do not hide independent verification, review, and promotion lifecycles inside one overloaded status field.

## 11. API Surface

Chapter 4.5 needs backend contracts that Chapter 5 can consume:

- candidate list for a workspace/run
- candidate detail with evidence, verification, contradictions, derivations, and provenance
- accept/reject candidate
- verification-detail endpoint
- promotion status

Exact route naming can follow existing API conventions.

## 12. Integration with Current Research Completion

Current research completion reaches automatic promotion in `app/workers/tasks.py`.

Target flow:

```text
ODR completes
    ↓
ResearchReport / ResearchArtifact
    ↓
verification + critique
    ↓
candidate records
    ↓
PENDING_REVIEW
    ↓
user decision
    ↓
promotion service
    ↓
KnowledgeMemory / Output KG
```

A research run may be `completed` while its candidates remain `pending review`, `accepted`, or `rejected`.

Research completion and promotion acceptance are separate concepts.

## 13. Scalability

Verification should not multiply full research cost unnecessarily.

Use:

- batch verification
- evidence deduplication
- cached verification keyed by claim/evidence/version
- deterministic checks before LLM verification
- asynchronous critic work
- bounded candidates and evidence per claim
- idempotent promotion

Rejecting one candidate must not rerun the full research run.

## 14. Security and Isolation

Every operation remains scoped by owner and workspace, with candidate/artifact ownership checks.

A user must not be able to inspect, decide, or promote another workspace's candidates or evidence.

Verification services must use canonical workspace authorization and must not bypass it.

## 15. Testing Requirements

Tests should cover:

- invalid citation IDs
- semantic support / contradiction / irrelevance
- deterministic derivation correctness and failure cases
- contradiction representation
- candidate lifecycle transitions
- accept/reject behavior
- idempotent promotion
- rejection preventing promotion
- research-derived data never becoming Ground evidence
- end-to-end accepted promotion
- end-to-end rejected candidate with no durable promotion

Critical scenarios:

```text
Research → evidence → candidate → verification → accept → KnowledgeMemory / Output KG
```

and:

```text
Research → candidate → reject → no durable promotion
```

## 16. Completion Criteria

Chapter 4.5 is complete when:

1. Referential citation integrity remains enforced.
2. Semantic support is represented explicitly.
3. Deterministic derivations can be verified.
4. Contradictory evidence can be represented and surfaced.
5. Research claims can pass through a critic stage.
6. Research output becomes explicit promotion candidates.
7. Users can accept/reject candidates through backend APIs.
8. Promotion is idempotent and auditable.
9. Accepted research memory remains excluded from Ground evidence.
10. Accepted Output KG objects retain provenance and verification state.
11. Research completion is separated from promotion acceptance.
12. All candidate, verification, review, and promotion paths are workspace-isolated.
13. Chapter 5 can build the review UI entirely on these backend contracts.

## 17. Relationship to Chapters 4 and 5

Chapter 4 provides the unified conversation, state, memory, workspace, and backend integration foundation.

Chapter 4.5 adds the trust boundary:

`memory/state → verification → review → promotion`

Chapter 5 consumes these contracts for candidate review, provenance inspection, contradiction display, derivation hover cards, graph interaction, and Ground/Research UI.

Chapter 4.5 is therefore the final backend quality/governance layer before frontend implementation.
