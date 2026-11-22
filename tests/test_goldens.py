import json

from audit_rag.paths import project_root

NOTE = "approved by owner 2026-11-22; q06/q12/q16/q17/q18 key points filled from source text"
THIN = {"q06", "q12", "q16", "q17", "q18"}
MUST_REFUSE = {"q19", "q20"}


def _rows() -> list[dict]:
    path = project_root() / "evals" / "golden_seed.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_all_twenty_goldens_are_approved() -> None:
    rows = _rows()
    assert [r["id"] for r in rows] == [f"q{i:02d}" for i in range(1, 21)]
    for row in rows:
        assert row["status"] == "approved"
        assert row["reviewer_note"] == NOTE
        assert row["question"].strip()
        assert row["proposed_answer_key_points"]
        if row["id"] in MUST_REFUSE:
            assert row["must_refuse"] is True
            assert row["proposed_chunk_ids"] == []
            assert row["proposed_doc_ids"] == []
        else:
            assert row["must_refuse"] is False
            assert row["proposed_chunk_ids"]
            assert row["proposed_doc_ids"]
        if row["id"] in THIN:
            assert len(row["proposed_answer_key_points"]) >= 3
