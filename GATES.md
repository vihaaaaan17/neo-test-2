# GATES: 04: Normalization & Provenance Services

- [x] Create `app/services/research/normalization.py`.
  - CHECK: `cat app/services/research/normalization.py | grep ResearchNormalizationService | wc -l`
  - EXPECT: `>0`
  - EVIDENCE: 1

- [x] Implement evidence fingerprinting logic.
  - CHECK: `cat app/services/research/normalization.py | grep generate_fingerprint | wc -l`
  - EXPECT: `>0`
  - EVIDENCE: 1

- [x] Create `app/services/research/provenance.py`.
  - CHECK: `cat app/services/research/provenance.py | grep ResearchProvenanceService | wc -l`
  - EXPECT: `>0`
  - EVIDENCE: 1

- [x] Implement source mapping logic.
  - CHECK: `cat app/services/research/provenance.py | grep resolve_source | wc -l`
  - EXPECT: `>0`
  - EVIDENCE: 1

- [x] Write unit tests verifying fingerprinting and unresolved sources.
  - CHECK: `pytest tests/unit/services/research/test_normalization_provenance.py`
  - EXPECT: `passed`
  - EVIDENCE: 5 passed in 2.73s
