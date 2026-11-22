"""Render a static HTML eval dashboard from a report dict."""

from __future__ import annotations

import html
from pathlib import Path

from audit_rag.theme import page_end, page_start, render_footer, render_header


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def render_dashboard(report: dict, path: Path) -> None:
    m = report["metrics"]
    method = report["method"]
    rows = []
    for rec in report["records"]:
        status = "refuse" if rec["did_refuse"] else "answer"
        expected = "must refuse" if rec["must_refuse"] else "must answer"
        ok = (rec["did_refuse"] and rec["must_refuse"]) or (
            (not rec["did_refuse"]) and (not rec["must_refuse"])
        )
        pill = "pass" if ok else "fail"
        rows.append(
            "<tr class='{cls}'><td>{id}</td><td>{q}</td><td>{expected}</td><td>{status}</td>"
            "<td>{cite}</td><td>{faith}</td><td><span class='pill {pill}'>{ok}</span></td></tr>".format(
                cls="ok" if ok else "bad",
                id=html.escape(str(rec["id"])),
                q=html.escape(rec["question"][:140]),
                expected=html.escape(expected),
                status=html.escape(status),
                cite=f"{rec['citation_accuracy']:.2f}",
                faith=f"{rec['faithfulness']:.2f}",
                pill=pill,
                ok=pill,
            )
        )
    failures = []
    for rec in report["records"]:
        refuse_fail = rec["must_refuse"] != rec["did_refuse"]
        cite_fail = (not rec["did_refuse"]) and rec["citation_accuracy"] < 1.0
        if refuse_fail or cite_fail:
            failures.append(
                "<li><strong>{id}</strong> {q}<pre>{ans}</pre></li>".format(
                    id=html.escape(str(rec["id"])),
                    q=html.escape(rec["question"]),
                    ans=html.escape(rec["answer"][:800]),
                )
            )
    fail_html = (
        "<ul class='failures'>" + "".join(failures) + "</ul>"
        if failures
        else "<p class='note'>No refusal or citation failures in this run.</p>"
    )
    embedder = html.escape(str(method.get("embedder", "")))
    generator = html.escape(str(method.get("generator", "")))
    page = (
        page_start("Eval dashboard · audit-rag-assistant")
        + render_header("dashboard")
        + f"""
<main class="wrap">
  <h1 class="page-title">Eval dashboard</h1>
  <p class="note">Embedder: {embedder}. Generator: {generator}.
  Metrics are lexical and reproducible; they are not an LLM-as-judge score.</p>
  <div class="metrics">
    <div class="metric"><span>Recall@10 (all gold)</span><strong>{_pct(m['recall@10_all'])}</strong></div>
    <div class="metric"><span>Mean recall@10</span><strong>{_pct(m['mean_recall@10'])}</strong></div>
    <div class="metric"><span>MRR@10</span><strong>{m['mrr@10']:.3f}</strong></div>
    <div class="metric"><span>Doc recall@10</span><strong>{_pct(m['doc_recall@10'])}</strong></div>
    <div class="metric"><span>Recall@5 (all gold)</span><strong>{_pct(m['recall@5_all'])}</strong></div>
    <div class="metric"><span>Mean recall@5</span><strong>{_pct(m['mean_recall@5'])}</strong></div>
    <div class="metric"><span>Harness time</span><strong>{m.get('elapsed_ms', 0):.0f} ms</strong></div>
    <div class="metric"><span>Citation accuracy</span><strong>{_pct(m['citation_accuracy'])}</strong></div>
    <div class="metric"><span>Faithfulness (lexical)</span><strong>{_pct(m['faithfulness'])}</strong></div>
    <div class="metric"><span>Refusal accuracy</span><strong>{_pct(m['refusal_accuracy'])}</strong></div>
  </div>
  <h2>Per-question results</h2>
  <div class="table-wrap">
  <table>
    <thead><tr><th>ID</th><th>Question</th><th>Expected</th><th>System</th><th>Cite</th><th>Faith</th><th>Refusal</th></tr></thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
  </div>
  <h2>Failures</h2>
  {fail_html}
  <h2>Method notes</h2>
  <ul class="method-notes">
    <li>Recall@k (all gold): {html.escape(method['recall_at_k_all'])}</li>
    <li>Mean recall@k: {html.escape(method['mean_recall_at_k'])}</li>
    <li>MRR: {html.escape(method['mrr'])}</li>
    <li>Citation accuracy: {html.escape(method['citation_accuracy'])}</li>
    <li>Faithfulness: {html.escape(method['faithfulness'])}</li>
    <li>Refusal accuracy: {html.escape(method['refusal_accuracy'])}</li>
    <li>Refusal rule: {html.escape(method.get('refusal_rule') or 'See README Results.')}</li>
  </ul>
</main>
"""
        + render_footer()
        + page_end()
    )
    path.write_text(page, encoding="utf-8")
