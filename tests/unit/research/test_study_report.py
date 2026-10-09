"""StudyReportCompiler: explicit-request detection, claim-level citation integrity, prompt bounds (pure, no DB)."""
import json

import pytest

from app.services.chat.service import resolve_research_routing
from app.services.research.study_report import (
    CatalogEntry,
    StudyMaterial,
    build_prompt,
    compose_paper,
    is_relevant,
    is_study_report_request,
    render_structured,
    validate_citations,
)


@pytest.mark.parametrize("msg", [
    "Compile everything we've discussed into a research paper",
    "Create a paper from this study session",
    "Please write up a report of what we have covered so far",
    "Turn our discussion into a research paper",
])
def test_explicit_compile_requests_are_detected(msg):
    assert is_study_report_request(msg)


@pytest.mark.parametrize("msg", [
    "Write a report on solar panel efficiency",
    "What does the paper by Vaswani et al. say about attention?",
    "Generate a summary of quantum dots",
    "How do research papers get peer reviewed?",
])
def test_ordinary_questions_are_not_compile_requests(msg):
    assert not is_study_report_request(msg)


def _catalog():
    return [
        CatalogEntry(n=1, kind="workspace_source", ref_id="src-1", title="lecture-notes.pdf",
                     excerpt="Self-attention weighs tokens by learned relevance scores.",
                     check_text="Self-attention weighs tokens by learned relevance scores computed from queries and keys."),
        CatalogEntry(n=2, kind="research_evidence", ref_id="ev-2", title="RAG overview", url="https://example.org/rag",
                     excerpt="Retrieval-augmented generation retrieves documents to ground answers.",
                     check_text="Retrieval-augmented generation retrieves documents to ground answers and reduce hallucinations."),
        CatalogEntry(n=3, kind="research_evidence", ref_id="ev-3", title="Fine-tuning study", url="https://example.org/ft",
                     excerpt="Fine-tuning alone did not reduce hallucinations in the benchmark.",
                     check_text="Fine-tuning alone did not reduce hallucinations in the benchmark; retrieval did."),
    ]


def _paper(statements, title="Paper"):
    return json.dumps({"title": title, "sections": [{"heading": "Findings", "statements": statements}]})


def test_finding_with_a_verbatim_supporting_passage_is_supported():
    paper = compose_paper(_paper([{"text": "Retrieval-augmented generation retrieves documents to ground answers.",
                                   "kind": "finding", "citations": [2],
                                   "support": [{"n": 2, "quote": "retrieves documents to ground answers and reduce hallucinations"}]}]),
                          _catalog())
    assert paper.structured and paper.claims["supported"] == 1
    assert "ground answers. [2]" in paper.content and "[Related source" not in paper.content
    record = paper.claims["records"][0]
    assert record["support_level"] == "verified_passage" and record["citations"][0]["quote_verified"] is True
    refs = paper.content.split("## References")[-1]
    assert "[2] RAG overview - https://example.org/rag (research evidence ev-2)" in refs and "ev-3" not in refs


def test_fabricated_citation_is_dropped_and_the_claim_is_marked_unsupported():
    paper = compose_paper(_paper([{"text": "RAG cut hallucinations by 90 percent in all deployments.", "kind": "finding",
                                   "citations": [42]}]), _catalog())
    assert "[42]" not in paper.content and paper.invalid_markers == ["42"]
    assert "*[Unsupported by the collected evidence]* RAG cut hallucinations by 90 percent" in paper.content
    assert paper.claims["unsupported"] == 1


def test_citation_existence_relevance_and_passage_are_distinct_levels():
    claim = "Retrieval-augmented generation retrieves documents to ground answers."
    # exists + relevant, but no quote -> only "related source", visibly qualified (not counted as supported)
    p = compose_paper(_paper([{"text": claim, "kind": "finding", "citations": [2]}]), _catalog())
    assert p.claims["supported"] == 0 and p.claims["weakly_supported"] == 1
    assert "*[Related source cited; no supporting passage verified]* " + claim in p.content
    # exists + relevant, but the "quote" is not in the stored evidence -> recorded as unverified, still only related
    p = compose_paper(_paper([{"text": claim, "kind": "finding", "citations": [2],
                               "support": [{"n": 2, "quote": "retrieval eliminates all hallucinations in every deployment"}]}]),
                      _catalog())
    assert p.claims["supported"] == 0 and p.claims["unverified_quotes"] == [{"claim": claim, "citation": 2}]
    assert p.claims["records"][0]["citations"][0]["quote"] is None  # an unverified quote is never stored or shown
    # a verbatim quote that is unrelated to the claim does not verify it
    p = compose_paper(_paper([{"text": "Transformers were introduced by Google researchers in 2017.", "kind": "finding",
                               "support": [{"n": 2, "quote": "retrieves documents to ground answers and reduce hallucinations"}]}]),
                      _catalog())
    assert p.claims["supported"] == 0 and "*[Unsupported by the collected evidence]*" in p.content


def test_real_but_irrelevant_citation_does_not_make_a_claim_look_supported():
    paper = compose_paper(_paper([{"text": "Transformers were introduced by Google researchers in 2017.", "kind": "finding",
                                   "citations": [2]}]), _catalog())
    assert "[2]" not in paper.content.split("## References")[0]
    assert "*[Unsupported by the collected evidence]* Transformers were introduced" in paper.content
    assert paper.claims["irrelevant_citations"][0]["citation"] == 2
    assert "No collected evidence was cited." in paper.content


def test_hypotheses_interpretations_calculations_and_disagreements_are_labelled():
    paper = compose_paper(_paper([
        {"text": "Retrieval may matter more than fine-tuning for factuality.", "kind": "hypothesis", "citations": []},
        {"text": "The session suggests retrieval documents ground answers best.", "kind": "interpretation", "citations": [2]},
        {"text": "Halving retrieved documents halves prompt length.", "kind": "calculation", "citations": []},
        {"text": "Sources differ on whether fine-tuning reduces hallucinations.", "kind": "disagreement", "citations": [2, 3]},
        {"text": "Sources differ on attention scores.", "kind": "disagreement", "citations": [1]},
        {"text": "This paper covers 3 sessions of study.", "kind": "framing", "citations": []},
    ]), _catalog())
    c = paper.content
    assert "*Hypothesis (not established):* Retrieval may matter more" in c
    assert "*Interpretation:* The session suggests" in c
    assert "halves prompt length. *(computed during the session; not externally verified)*" in c
    assert "*Sources disagree:* Sources differ on whether fine-tuning reduces hallucinations. [2, 3]" in c
    assert "*[Unsupported - a disagreement needs two supporting sources]* Sources differ on attention" in c
    # A "framing" sentence carrying a number is treated as a factual claim and needs support.
    assert "*[Unsupported by the collected evidence]* This paper covers 3 sessions" in c


def test_fallback_markdown_validation_marks_sentences_that_lose_their_citations():
    model_output = (
        "# Paper\n\nSelf-attention weighs tokens by relevance scores [1]. RAG retrieves documents to ground answers [2, 99]. "
        "Made up claim about quantum gravity [42].\n"
        "See [this blog](https://invented.example.com/post) and [the overview](https://example.org/rag).\n\n"
        "## References\n\n[1] Some invented reference that the model wrote\n"
    )
    paper = validate_citations(model_output, _catalog())
    body = paper.content.split("## References")[0]
    assert "relevance scores [1]" in body and "ground answers [2]" in body
    assert "[99]" not in body and "[42]" not in body
    assert "*[Unsupported by the collected evidence]* Made up claim about quantum gravity" in body
    assert "invented.example.com" not in paper.content and "this blog" in body
    assert "Some invented reference" not in paper.content
    assert any("did not return structured claims" in w for w in paper.warnings)


def test_compose_falls_back_when_the_model_ignores_the_json_format():
    paper = compose_paper("# Paper\n\nRAG retrieves documents to ground answers [2].", _catalog())
    assert not paper.structured and "[2]" in paper.content


def test_without_catalog_every_finding_is_unsupported():
    paper = render_structured(json.loads(_paper([{"text": "RAG retrieves documents.", "kind": "finding", "citations": [1]}])), [])
    assert "*[Unsupported by the collected evidence]*" in paper.content and "No collected evidence was cited." in paper.content


def test_sections_merely_named_sources_are_kept():
    paper = validate_citations("# Paper\n\n## Sources of error\n\nSelf-attention weighs tokens [1].", _catalog())
    assert "## Sources of error" in paper.content and "weighs tokens [1]" in paper.content


def test_relevance_uses_stored_evidence_text():
    entry = _catalog()[2]
    assert is_relevant("Fine-tuning alone did not reduce hallucinations.", entry)
    assert not is_relevant("Photosynthesis converts light into chemical energy in plants.", entry)


def test_prompt_contains_the_session_requests_structured_claims_and_forbids_new_sources():
    material = StudyMaterial(
        turns=[{"turn_id": "t1", "sequence": 1, "mode": "ground", "user": "What is attention?", "assistant": "It weighs tokens."}],
        catalog=_catalog(), notes=[{"entry_id": "n1", "type": "hypothesis", "content": "RAG reduces hallucination."}], run_ids=[],
    )
    prompt = build_prompt("Compile this session into a paper", material)
    assert "What is attention?" in prompt and "RAG reduces hallucination." in prompt
    assert "[2] (web evidence) RAG overview <https://example.org/rag>" in prompt
    assert '"kind": "finding"' in prompt and "Do not add facts, sources or URLs" in prompt
    assert "computed from queries and keys" not in prompt  # validation text is not sent to the model


def test_research_routing_resolution():
    assert resolve_research_routing(None) == ("auto", None)
    assert resolve_research_routing({}) == ("auto", None)
    assert resolve_research_routing({"engine": "storm"}) == ("explicit", "storm")
    assert resolve_research_routing({"routing_mode": "auto"}) == ("auto", None)
    assert resolve_research_routing({"routing_mode": "explicit", "engine": "gpt_researcher"}) == ("explicit", "gpt_researcher")
