"""
Warehouse Management AI Chatbot
Generative AI chatbot using Retrieval-Augmented Generation (RAG) and data tools over
warehouse orders, inventory, shipping delays, and labor attendance.
"""
import json
import os

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Warehouse Management AI Chatbot", page_icon="📦", layout="wide")


def secret(name, default=None):
    try:
        return st.secrets.get(name, os.environ.get(name, default))
    except Exception:
        return os.environ.get(name, default)


if secret("ANTHROPIC_API_KEY"):
    os.environ["ANTHROPIC_API_KEY"] = secret("ANTHROPIC_API_KEY")


@st.cache_resource(show_spinner="Loading warehouse data and knowledge base...")
def load():
    import data_store
    import rag
    return data_store, rag


ds, rag = load()
MODEL = secret("CLAUDE_MODEL", "claude-sonnet-5-5")


@st.cache_resource
def client_for(key):
    return rag.get_client() if key else None


client = client_for(os.environ.get("ANTHROPIC_API_KEY"))
T = ds.TABLES
orders, inv, ship, att = T["warehouse_orders"], T["inventory"], T["shipping_delays"], T["labor_attendance"]

EXAMPLES = [
    "Which orders are at the highest risk on 2026-11-13 and what should I do?",
    "Why is SO-94198 likely to ship late?",
    "Which products are low stock and where are they located?",
    "What are the main reasons for shipping delays, and which carrier performs worst?",
    "How does labor attendance on Mondays compare with other days?",
    "Which associates have the most absences?",
    "What happened on 2026-10-12 across orders, labor, and shipping?",
    "Is there a link between staffing and shipping delays?",
    "Summarize warehouse performance for October 2026.",
]

st.title("📦 Warehouse Management AI Chatbot")
st.caption("Ask about at-risk orders, inventory, shipping delays, and labor attendance. Answers come from retrieved "
           "warehouse knowledge and live queries on the data (RAG with tool use). All data is synthetic.")

chat_tab, dash_tab, data_tab, about_tab = st.tabs(["Chat", "Dashboard", "Data explorer", "About"])

# ------------------------------------------------------------------ chat
with chat_tab:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if client is None:
        st.warning("The language model is not configured. Add ANTHROPIC_API_KEY in the app's Secrets settings.")

    with st.expander("Example questions", expanded=not st.session_state.messages):
        cols = st.columns(3)
        clicked = None
        for i, q in enumerate(EXAMPLES):
            if cols[i % 3].button(q, key=f"ex{i}", width="stretch"):
                clicked = q
    if st.session_state.messages and st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

    def show_trace(sources, tools):
        if not sources and not tools:
            return
        with st.expander(f"How this was answered: {len(sources)} knowledge passages, {len(tools)} data queries"):
            if sources:
                st.markdown("**Retrieved passages**\n" + "\n".join(f"{i + 1}. {s}" for i, s in enumerate(sources)))
            for t in tools:
                st.markdown(f"**Query:** `{t['tool']}`")
                st.code(json.dumps(t["input"], indent=1), language="json")
                try:
                    res = json.loads(t["output"])
                    rows = res.get("result") if isinstance(res, dict) else None
                    if rows:
                        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
                    else:
                        st.json(res, expanded=False)
                except Exception:
                    st.text(t["output"][:2000])

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if m["role"] == "assistant":
                show_trace(m.get("sources", []), m.get("tools", []))

    prompt = st.chat_input("Ask about orders, inventory, shipping, or labor") or clicked
    if prompt:
        with st.chat_message("user"):
            st.markdown(prompt)
        history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
        with st.chat_message("assistant"):
            with st.spinner("Retrieving knowledge and querying the data..."):
                try:
                    text, sources, tools = rag.answer(prompt, history, client, MODEL)
                except Exception as e:
                    text, sources, tools = f"Sorry, the request failed: {e}", [], []
            st.markdown(text)
            show_trace(sources, tools)
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.messages.append({"role": "assistant", "content": text, "sources": sources, "tools": tools})

# ------------------------------------------------------------------ dashboard
with dash_tab:
    k = st.columns(6)
    k[0].metric("At-risk orders", f"{len(orders):,}", f"{(orders.risk_tier == 'Critical').sum()} critical", delta_color="off")
    k[1].metric("Avg delay probability", f"{orders.delay_probability.mean():.0%}")
    k[2].metric("Shipments on time", f"{1 - ship.is_delayed.mean():.0%}", f"{ship.is_delayed.sum()} delayed", delta_color="off")
    k[3].metric("Avg days late (delayed)", f"{ship[ship.is_delayed == 1].Delay_Days.mean():.1f}")
    k[4].metric("Low stock products", f"{(inv.Inventory_Status == 'Low Stock').sum()} of {len(inv)}")
    k[5].metric("Attendance rate", f"{att.is_present.mean():.1%}", f"{att.is_absent.sum()} absences", delta_color="off")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**At-risk orders by zone**")
        st.bar_chart(orders.dominant_zone.value_counts().sort_index().rename("orders"), y_label="orders", x_label="zone")
        st.markdown("**Shipping delays by reason**")
        st.bar_chart(ship[ship.is_delayed == 1].Delay_Reason.value_counts().rename("delayed shipments"),
                     horizontal=True, x_label="delayed shipments", y_label="")
    with c2:
        st.markdown("**Attendance rate by day of week (%)**")
        order_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        st.bar_chart((att.groupby("day_of_week").is_present.mean() * 100).reindex(order_days).rename("attendance %"),
                     y_label="attendance %", x_label="", sort=False)
        st.markdown("**Shipping delay rate by carrier (%)**")
        st.bar_chart((ship.groupby("Carrier").is_delayed.mean() * 100).rename("delay rate %"), y_label="delay rate %", x_label="")

    st.markdown("**At-risk orders per week and pickers present per day (weekly average)**")
    wk = pd.DataFrame({
        "at-risk orders": orders.groupby(orders.release_ts.dt.to_period("W").dt.start_time).size(),
    })
    pk = att[att.role == "Picker"].groupby("date").is_present.sum()
    pk.index = pd.to_datetime(pk.index)
    w1, w2 = st.columns(2)
    w1.line_chart(wk, y_label="orders per week", x_label="")
    w2.line_chart(pk.groupby(pk.index.to_period("W").start_time).mean().rename("pickers present"),
                  y_label="pickers present per day", x_label="")

    l1, l2 = st.columns(2)
    with l1:
        last = orders.release_date.max()
        st.markdown(f"**Highest-risk orders on {last}**")
        st.dataframe(orders[orders.release_date == last].nlargest(10, "delay_probability")[
            ["order_id", "dominant_zone", "lines_count", "hours_to_cutoff", "delay_probability", "suggested_action"]],
            hide_index=True, width="stretch",
            column_config={"delay_probability": st.column_config.ProgressColumn("delay probability", format="%.2f",
                                                                                min_value=0.0, max_value=1.0)})
    with l2:
        st.markdown("**Low stock products**")
        st.dataframe(inv[inv.Inventory_Status == "Low Stock"].sort_values("units_above_reorder")[
            ["Product_ID", "Category", "Stock_Available", "Reorder_Level", "Warehouse_Location"]],
            hide_index=True, width="stretch")

# ------------------------------------------------------------------ data explorer
with data_tab:
    names = {"Warehouse orders (at risk)": "warehouse_orders", "Inventory": "inventory",
             "Shipping delays": "shipping_delays", "Labor attendance": "labor_attendance"}
    label = st.radio("Table", list(names), horizontal=True)
    name = names[label]
    df = T[name]
    st.caption(ds.DESCRIPTIONS[name])
    q = st.text_input("Filter rows containing", placeholder="e.g. SO-94198, Low Stock, Carrier A, EMP105, 2026-10-12")
    view = df
    if q.strip():
        mask = df.astype(str).apply(lambda c: c.str.contains(q.strip(), case=False, regex=False)).any(axis=1)
        view = df[mask]
    st.write(f"{len(view):,} of {len(df):,} rows")
    st.dataframe(view.head(3000), hide_index=True, width="stretch")
    st.download_button(f"Download {name}.csv", view.to_csv(index=False).encode(), file_name=f"{name}.csv",
                       mime="text/csv")

# ------------------------------------------------------------------ about
with about_tab:
    st.markdown(open(os.path.join(os.path.dirname(__file__), "knowledge/solution_overview.md")).read())
