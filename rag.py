"""
RAG layer: TF-IDF retrieval over the knowledge documents, direct ID lookups, and the
Claude tool-use loop that answers questions from the warehouse data.
"""
import json
import os
import re
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

import data_store as ds

BASE = Path(__file__).parent
TOP_DOCS = 4
MAX_TOOL_ROUNDS = 6


def _chunks():
    out = []
    for path in sorted((BASE / "knowledge").glob("*.md")):
        text = path.read_text()
        title = text.splitlines()[0].lstrip("# ").strip()
        for part in re.split(r"\n(?=## )", text):
            heading = part.splitlines()[0].lstrip("# ").strip()
            if len(part.strip()) < 40:
                continue
            out.append({"source": path.name if heading == title else f"{path.name} > {heading}",
                        "text": part.strip() if heading == title else f"{title}\n{part.strip()}"})
    return out


CHUNKS = _chunks()
_vec = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", sublinear_tf=True)
_mat = _vec.fit_transform([c["text"] for c in CHUNKS])
ID_RE = re.compile(r"\b(SO-\d{5}|ORD\d{5}|PRD\d{4}|EMP\d{3})\b", re.I)
DATE_RE = re.compile(r"\b(2026-\d{2}-\d{2})\b")


def retrieve(question):
    """Knowledge passages plus direct lookups for any IDs or dates in the question."""
    ctx = []
    sims = linear_kernel(_vec.transform([question]), _mat).ravel()
    for i in sims.argsort()[::-1][:TOP_DOCS]:
        if sims[i] > 0.03:
            ctx.append({"source": CHUNKS[i]["source"], "text": CHUNKS[i]["text"]})
    for rid in sorted(set(m.upper() for m in ID_RE.findall(question)))[:4]:
        ctx.append({"source": f"record lookup > {rid}", "text": ds.run_tool("get_record", {"record_id": rid})})
    for d in sorted(set(DATE_RE.findall(question)))[:2]:
        ctx.append({"source": f"daily snapshot > {d}", "text": ds.run_tool("daily_snapshot", {"date": d})})
    return ctx


SYSTEM = f"""You are the Warehouse Operations Assistant for a distribution center. You help shift supervisors and \
managers understand at-risk orders, inventory, shipping delays, and labor attendance, and decide what to do.

How to answer:
- Ground every number in the provided context passages or in results from your data tools. Never estimate or invent \
order IDs, counts, rates, or dates.
- The context passages may already answer the question; if they do, answer directly without calling tools.
- Otherwise call the data tools. Prefer one well-built query_table call with filters, group_by, and metrics over many \
small calls. For rates use mean of the 0/1 columns (is_delayed, is_present, is_absent, is_late).
- Dates in the data run from 2026-07-01 to 2026-11-14. Treat "today" as 2026-11-13 for orders and 2026-11-14 for attendance \
unless the user gives a date.
- When explaining an at-risk order, give the delay probability as a percentage, its risk drivers in plain words, and the \
suggested action. Link labor, inventory, or shipping data when it helps explain the situation.
- Be concise and practical: a direct answer first, then short bullets or a small markdown table if useful.
- If the data cannot answer the question, say so and suggest a related question it can answer.
- Do not use em dashes or en dashes; use commas, colons, or hyphens instead.

## Data tables
{ds.schema_text()}
"""


def get_client():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    import anthropic
    return anthropic.Anthropic(api_key=key)


def answer(question, history, client, model):
    """Run retrieval and the tool-use loop. Returns (answer_text, sources, tool_calls)."""
    ctx = retrieve(question)
    numbered = "\n\n".join(f"[{i + 1}] {c['source']}\n{c['text']}" for i, c in enumerate(ctx))
    sources = [c["source"] for c in ctx]
    tool_log = []
    if client is None:
        return ("The language model is not configured yet, so here is what retrieval found:\n\n" + numbered[:3500],
                sources, tool_log)

    messages = list(history[-6:])
    messages.append({"role": "user", "content": f"Context passages:\n\n{numbered or '(none)'}\n\nQuestion: {question}"})
    system = [{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}]
    for _ in range(MAX_TOOL_ROUNDS):
        resp = client.messages.create(model=model, max_tokens=1200, system=system, tools=ds.TOOLS, messages=messages)
        if resp.stop_reason != "tool_use":
            text = "".join(b.text for b in resp.content if b.type == "text").strip()
            return text, sources, tool_log
        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for b in resp.content:
            if b.type == "tool_use":
                out = ds.run_tool(b.name, b.input)
                tool_log.append({"tool": b.name, "input": b.input, "output": out})
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": out[:12000]})
        messages.append({"role": "user", "content": results})
    return ("I could not finish the analysis within the query limit. Try a narrower question, for example one month, "
            "one zone, or one carrier.", sources, tool_log)
