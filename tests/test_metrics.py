from audit_rag.eval.metrics import (
    chunk_supports_claim,
    citation_accuracy,
    refusal_accuracy,
    retrieval_scores,
)
from audit_rag.generate.answer import REFUSAL_TEXT, Answer
from audit_rag.index.store import SearchHit


def _hit(chunk_id: str, text: str) -> SearchHit:
    return SearchHit(
        chunk_id=chunk_id,
        doc_id=chunk_id.split("#")[0],
        title="t",
        section="s",
        text=text,
        source_url="https://example.test",
        license="MIT",
        score=1.0,
    )


def test_retrieval_scores_recall_and_mrr() -> None:
    records = [
        {
            "must_refuse": False,
            "gold_chunk_ids": ["a#c1", "a#c2"],
            "retrieved_chunk_ids": ["a#c1", "z#c0", "a#c2"],
            "gold_doc_ids": ["a"],
            "retrieved_doc_ids": ["a", "z", "a"],
        },
        {
            "must_refuse": True,
            "gold_chunk_ids": [],
            "retrieved_chunk_ids": ["x#c0"],
            "gold_doc_ids": [],
            "retrieved_doc_ids": ["x"],
        },
    ]
    scores = retrieval_scores(records, k=3)
    assert scores.n_scored == 1
    assert scores.recall_at_k_all == 1.0
    assert scores.mean_recall_at_k == 1.0
    assert scores.mrr == 1.0
    assert scores.doc_recall_at_k == 1.0


def test_citation_accuracy_requires_overlap() -> None:
    hits = [_hit("swc-107#c4", "Use the Checks-Effects-Interactions pattern before external calls.")]
    good = Answer(
        text="Use the Checks-Effects-Interactions pattern before external calls. [1:swc-107#c4]",
        refused=False,
        reason="ok",
        used_chunk_ids=["swc-107#c4"],
    )
    score, _ = citation_accuracy(good, hits)
    assert score == 1.0

    bad = Answer(
        text="The DAO lost exactly nine million ether. [1:swc-107#c4]",
        refused=False,
        reason="ok",
        used_chunk_ids=["swc-107#c4"],
    )
    score, _ = citation_accuracy(bad, hits)
    assert score == 0.0


def test_refusal_accuracy_and_supported_claim_helper() -> None:
    acc, breakdown = refusal_accuracy(
        [
            {"must_refuse": True, "did_refuse": True},
            {"must_refuse": True, "did_refuse": False},
            {"must_refuse": False, "did_refuse": False},
            {"must_refuse": False, "did_refuse": True},
        ]
    )
    assert breakdown == {
        "true_refuse": 1,
        "false_refuse": 1,
        "true_answer": 1,
        "false_answer": 1,
        "n": 4,
    }
    assert acc == 0.5
    assert chunk_supports_claim("Use a reentrancy lock", "Use a reentrancy lock such as ReentrancyGuard.")
    _ = REFUSAL_TEXT
