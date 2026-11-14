"""
Retrieval layer for the Warehouse Management AI Chatbot (RAG).
Builds TF-IDF indexes over the knowledge documents and scored orders.
"""
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

BASE = Path(__file__).parent
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")
TOP_DOCS, TOP_ORDERS = 5, 5

# ------------------------------------------------------------------ knowledge base
def load_doc_chunks():
    """Split each markdown file into one chunk per '## ' section."""
    chunks = []
    for path in sorted((BASE / "knowledge").glob("*.md")):
        text = path.read_text()
        title = text.splitlines()[0].lstrip("# ").strip()
        parts = re.split(r"\n(?=## )", text)
        for part in parts:
            heading = part.splitlines()[0].lstrip("# ").strip()
            body = part.strip()
            if len(body) < 40:
                continue
            chunks.append({"source": f"{path.name} > {heading}" if heading != title else path.name,
                           "text": body if heading == title else f"{title}\n{body}"})
    return chunks


orders = pd.read_csv(BASE / "data/scored_orders.csv")
orders["is_late_text"] = np.where(orders.is_late == 1, "shipped late", "shipped on time")


def order_text(r):
    return (f"Order {r.order_id}: released {r.release_ts} ({r.day_of_week}), carrier {r.carrier_code} cutoff "
            f"{r.required_ship_by_ts}, {r.hours_to_cutoff} hours to cutoff at release. Customer {r.customer_id}, "
            f"{r.sla_tier} SLA. {r.lines_count} lines, {r.units} units, {r.zones_touched} zones, main zone "
            f"{r.dominant_zone}, {r.reserve_lines} lines only in reserve. Zone backlog ratio {r.zone_backlog_ratio}, "
            f"{r.pickers_on_shift} pickers on shift ({r.zone_pickers_on_shift} in zone {r.dominant_zone}), "
            f"{r.units_per_picker} units per picker. Delay probability {r.delay_probability:.2f}, risk level "
            f"{r.risk_level}. Risk drivers: {r.risk_drivers}. Protective factors: {r.protective_factors}. "
            f"Suggested action: {r.suggested_action}. Outcome: {r.is_late_text} (actual ship {r.actual_ship_ts}).")


orders["text"] = [order_text(r) for r in orders.itertuples()]
order_by_id = dict(zip(orders.order_id, orders.text))

doc_chunks = load_doc_chunks()
doc_vec = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", sublinear_tf=True)
doc_matrix = doc_vec.fit_transform([c["text"] for c in doc_chunks])
ord_vec = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", sublinear_tf=True)
ord_matrix = ord_vec.fit_transform(orders.text)

RISK_WORDS = re.compile(r"\b(risk|risky|at.risk|flag|flagged|top|highest|urgent|dashboard|priorit|late today|watch)", re.I)
ORDER_WORDS = re.compile(r"\b(order|orders|SO-)\b", re.I)


def retrieve(question):
    """Return context passages and source labels for a question."""
    context, sources = [], []

    # 1. exact order lookups
    ids = sorted(set(m.upper() for m in re.findall(r"SO-\d{5}", question, re.I)))
    for oid in ids:
        if oid in order_by_id:
            context.append(order_by_id[oid]); sources.append(f"scored_orders.csv > {oid}")
        else:
            context.append(f"Order {oid} is not in the scored test period (April to June 2026)."); sources.append(f"lookup {oid}")

    # 2. knowledge document sections
    sims = linear_kernel(doc_vec.transform([question]), doc_matrix).ravel()
    for i in sims.argsort()[::-1][:TOP_DOCS]:
        if sims[i] > 0.02:
            context.append(doc_chunks[i]["text"]); sources.append(doc_chunks[i]["source"])

    # 3. highest-risk list when the user asks about risk or priorities
    if RISK_WORDS.search(question) and not ids:
        zone = re.search(r"\bzone\s+([A-D])\b", question, re.I)
        pool = orders[orders.risk_level == "High"]
        if zone:
            pool = pool[pool.dominant_zone == zone.group(1).upper()]
        top = pool.sort_values("delay_probability", ascending=False).head(10)
        if len(top):
            context.append("Highest-risk scored orders" + (f" in zone {zone.group(1).upper()}" if zone else "") + ":\n"
                           + "\n".join(top.text))
            sources.append("scored_orders.csv > top high-risk orders")

    # 4. similar order records for descriptive order questions
    if ORDER_WORDS.search(question) and not ids:
        osims = linear_kernel(ord_vec.transform([question]), ord_matrix).ravel()
        for i in osims.argsort()[::-1][:TOP_ORDERS]:
            if osims[i] > 0.05 and orders.text[i] not in "\n".join(context):
                context.append(orders.text[i]); sources.append(f"scored_orders.csv > {orders.order_id[i]}")
    return context, sources


SYSTEM = """You are the Warehouse Operations Assistant for a distribution center. You help shift supervisors \
understand which customer orders are at risk of missing their carrier cutoff, why, and what to do about it.

Rules:
- Answer only from the numbered context passages provided with each question. If they do not contain the answer, \
say you do not have that information and suggest what the user could ask instead.
- Cite passages inline with their numbers, like [1] or [2][4].
- For an order, give its delay probability as a percentage, the risk level, the top risk drivers in plain language, \
and the suggested action. Mention protective factors when relevant.
- Keep answers short and practical for a busy supervisor: a direct answer first, then bullets if useful.
- Never invent order IDs, numbers, or policies.
- Do not use em dashes or en dashes; use commas, colons, or hyphens instead."""


