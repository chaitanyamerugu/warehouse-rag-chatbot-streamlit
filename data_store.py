"""
Data layer for the Warehouse Management AI Chatbot.
Loads the four warehouse tables, adds helpful derived columns, and exposes safe query tools
that the language model can call to compute exact answers (no model-written code is executed).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).parent / "data"
MAX_ROWS = 50


def _load():
    o = pd.read_csv(DATA / "warehouse_orders.csv", parse_dates=["release_ts", "required_ship_by_ts"])
    o["release_date"] = o.release_ts.dt.strftime("%Y-%m-%d")
    o["release_month"] = o.release_ts.dt.strftime("%Y-%m")
    o["day_of_week"] = o.release_ts.dt.day_name()
    o["risk_tier"] = pd.cut(o.delay_probability, [0, 0.4, 0.6, 1.0], labels=["Elevated", "High", "Critical"]).astype(str)

    inv = pd.read_csv(DATA / "inventory.csv")
    inv["units_above_reorder"] = inv.Stock_Available - inv.Reorder_Level
    inv["stock_value_usd"] = (inv.Stock_Available * inv.Unit_Price_USD).round(2)
    inv["aisle"] = inv.Warehouse_Location.str.split("-").str[0]

    sh = pd.read_csv(DATA / "shipping_delays.csv", parse_dates=["Order_Date", "Expected_Ship_Date", "Actual_Ship_Date"])
    sh["order_month"] = sh.Order_Date.dt.strftime("%Y-%m")
    sh["expected_ship_weekday"] = sh.Expected_Ship_Date.dt.day_name()
    sh["is_delayed"] = (sh.Delivery_Status == "Delayed").astype(int)
    for c in ["Order_Date", "Expected_Ship_Date", "Actual_Ship_Date"]:
        sh[c] = sh[c].dt.strftime("%Y-%m-%d")

    la = pd.read_csv(DATA / "labor_attendance.csv", keep_default_na=False)
    la["month"] = la.date.str[:7]
    la["is_present"] = la.status.isin(["Present", "Late"]).astype(int)
    la["is_absent"] = la.status.isin(["Absent", "No Call No Show"]).astype(int)
    la["is_late"] = (la.status == "Late").astype(int)
    return {"warehouse_orders": o, "inventory": inv, "shipping_delays": sh, "labor_attendance": la}


TABLES = _load()

DESCRIPTIONS = {
    "warehouse_orders": "2,000 orders flagged at risk of missing their carrier cutoff (July 1 to November 13, 2026). One row per order with "
                        "the model's delay_probability (all are 0.28 or higher, so every order here is above the alert threshold), "
                        "SHAP risk_drivers, and the suggested_action.",
    "inventory": "100 products across 5 categories with stock on hand, reorder level, aisle-rack location, unit price, and status "
                 "(Low Stock means Stock_Available is at or below Reorder_Level).",
    "shipping_delays": "200 shipped orders (order dates September 1 to November 4, 2026) with expected and actual ship dates, "
                       "delivery status, delay days, delay reason, and carrier (Carrier A, B, C).",
    "labor_attendance": "Daily attendance for 60 warehouse associates (40 pickers, 10 packers, 6 forklift operators, 4 shift leads), "
                        "July 1 to November 14, 2026, Monday to Saturday. One row per associate per day.",
}


def schema_text():
    out = []
    for name, df in TABLES.items():
        out.append(f"### {name} ({len(df):,} rows)\n{DESCRIPTIONS[name]}\nColumns:")
        for c in df.columns:
            s = df[c]
            if pd.api.types.is_numeric_dtype(s):
                desc = f"number, {s.min():g} to {s.max():g}"
            elif pd.api.types.is_datetime64_any_dtype(s):
                desc = f"datetime, {s.min():%Y-%m-%d %H:%M} to {s.max():%Y-%m-%d %H:%M}"
            else:
                u = [str(x) for x in s.dropna().unique()]
                desc = f"text, values: {', '.join(sorted(u)[:12])}" if len(u) <= 12 else f"text, {len(u)} distinct, e.g. {', '.join(u[:3])}"
            out.append(f"- {c}: {desc}")
    return "\n".join(out)


# ------------------------------------------------------------------ tools
def _cast(series, value):
    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(value)
    if pd.api.types.is_numeric_dtype(series):
        if isinstance(value, list):
            return [float(v) for v in value]
        return float(value)
    return value


def _apply_filters(df, filters):
    for f in filters or []:
        col, op, val = f.get("column"), f.get("op", "="), f.get("value")
        if col not in df.columns:
            raise ValueError(f"Unknown column '{col}'. Available: {', '.join(df.columns)}")
        s = df[col]
        v = _cast(s, val) if op not in ("contains", "in") else val
        if op == "=":
            m = s.astype(str).str.lower() == str(val).lower() if s.dtype == object or pd.api.types.is_string_dtype(s) else s == v
        elif op == "!=":
            m = s.astype(str).str.lower() != str(val).lower() if pd.api.types.is_string_dtype(s) else s != v
        elif op == ">": m = s > v
        elif op == ">=": m = s >= v
        elif op == "<": m = s < v
        elif op == "<=": m = s <= v
        elif op == "contains": m = s.astype(str).str.contains(str(val), case=False, regex=False)
        elif op == "in":
            vals = [str(x).lower() for x in (val if isinstance(val, list) else [val])]
            m = s.astype(str).str.lower().isin(vals)
        elif op == "between":
            lo, hi = _cast(s, val[0]), _cast(s, val[1])
            m = (s >= lo) & (s <= hi)
        else:
            raise ValueError(f"Unsupported op '{op}'")
        df = df[m]
    return df


def _fmt(df):
    df = df.copy()
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            df[c] = df[c].dt.strftime("%Y-%m-%d %H:%M")
        elif pd.api.types.is_float_dtype(df[c]):
            df[c] = df[c].round(3)
    return df


def query_table(table, filters=None, group_by=None, metrics=None, columns=None, sort_by=None,
                ascending=False, limit=20):
    """Filter, group, aggregate, sort, and return rows from one table."""
    if table not in TABLES:
        raise ValueError(f"Unknown table '{table}'. Use one of: {', '.join(TABLES)}")
    df = _apply_filters(TABLES[table], filters)
    limit = max(1, min(int(limit or 20), MAX_ROWS))
    matched = len(df)
    if group_by or metrics:
        metrics = metrics or [{"column": df.columns[0], "agg": "count"}]
        agg_spec = {}
        for m in metrics:
            col, agg = m["column"], m.get("agg", "count")
            if col not in df.columns:
                raise ValueError(f"Unknown column '{col}'")
            agg_spec[f"{agg}_{col}"] = pd.NamedAgg(column=col, aggfunc={"avg": "mean"}.get(agg, agg))
        if group_by:
            out = df.groupby(group_by, observed=True).agg(**agg_spec).reset_index()
        else:
            out = pd.DataFrame({k: [df[v.column].agg(v.aggfunc)] for k, v in agg_spec.items()})
        if sort_by and sort_by in out.columns:
            out = out.sort_values(sort_by, ascending=ascending)
        elif len(out.columns) > len(group_by or []):
            out = out.sort_values(out.columns[-1], ascending=ascending)
        total_groups = len(out)
        return {"table": table, "rows_matched": matched, "groups": total_groups,
                "result": _fmt(out.head(limit)).to_dict("records")}
    if sort_by:
        df = df.sort_values(sort_by, ascending=ascending)
    if columns:
        df = df[[c for c in columns if c in df.columns]]
    return {"table": table, "rows_matched": matched, "rows_returned": min(limit, matched),
            "result": _fmt(df.head(limit)).to_dict("records")}


def get_record(record_id):
    """Look up an order (SO-), shipment (ORD), product (PRD), or associate (EMP) by ID."""
    rid = record_id.strip().upper()
    if rid.startswith("SO-"):
        t, col = "warehouse_orders", "order_id"
    elif rid.startswith("ORD"):
        t, col = "shipping_delays", "Order_ID"
    elif rid.startswith("PRD"):
        t, col = "inventory", "Product_ID"
    elif rid.startswith("EMP"):
        la = TABLES["labor_attendance"]
        e = la[la.employee_id == rid]
        if e.empty:
            return {"found": False, "id": rid}
        first = e.iloc[0]
        return {"found": True, "table": "labor_attendance", "employee_id": rid, "employee_name": first.employee_name,
                "role": first.role, "assigned_zone": first.assigned_zone, "shift": first["shift"],
                "employment_type": first.employment_type, "days_scheduled": len(e),
                "attendance_rate": round(e.is_present.mean(), 3), "days_absent": int(e.is_absent.sum()),
                "days_late": int(e.is_late.sum()), "pto_days": int((e.status == "PTO").sum()),
                "overtime_hours": float(e.overtime_hours.sum()),
                "status_counts": e.status.value_counts().to_dict(),
                "last_10_days": e.tail(10)[["date", "status", "clock_in", "clock_out", "hours_worked"]].to_dict("records")}
    else:
        return {"found": False, "id": rid, "note": "IDs start with SO-, ORD, PRD, or EMP"}
    df = TABLES[t]
    r = df[df[col].str.upper() == rid]
    return {"found": not r.empty, "table": t, "record": _fmt(r).to_dict("records")[0] if len(r) else None}


def daily_snapshot(date):
    """Everything that happened on one date across all four tables."""
    d = pd.to_datetime(date).strftime("%Y-%m-%d")
    o = TABLES["warehouse_orders"]; od = o[o.release_date == d]
    la = TABLES["labor_attendance"]; ld = la[la.date == d]
    sh = TABLES["shipping_delays"]; sd = sh[sh.Expected_Ship_Date == d]
    pickers = ld[ld.role == "Picker"]
    return {
        "date": d, "day_of_week": pd.to_datetime(d).day_name(),
        "at_risk_orders": {"count": len(od), "avg_delay_probability": round(od.delay_probability.mean(), 3) if len(od) else None,
                           "by_zone": od.dominant_zone.value_counts().to_dict(),
                           "top_5": _fmt(od.nlargest(5, "delay_probability")[["order_id", "dominant_zone", "lines_count", "hours_to_cutoff", "delay_probability", "suggested_action"]]).to_dict("records")},
        "labor": {"scheduled": len(ld), "present": int(ld.is_present.sum()), "absent": int(ld.is_absent.sum()),
                  "late": int(ld.is_late.sum()), "pto": int((ld.status == "PTO").sum()),
                  "attendance_rate": round(ld.is_present.mean(), 3) if len(ld) else None,
                  "pickers_present": int(pickers.is_present.sum()), "pickers_scheduled": len(pickers),
                  "present_by_zone": ld[ld.is_present == 1].assigned_zone.value_counts().to_dict(),
                  "overtime_hours": float(ld.overtime_hours.sum())},
        "shipments_expected": {"count": len(sd), "delayed": int(sd.is_delayed.sum()),
                               "records": sd[["Order_ID", "Delivery_Status", "Delay_Days", "Delay_Reason", "Carrier"]].to_dict("records")},
    }


TOOLS = [
    {
        "name": "query_table",
        "description": "Run an exact query on one warehouse table: filter rows, optionally group and aggregate, sort, and return up to 50 rows. "
                       "Use for counts, totals, averages, rankings, lists, and comparisons. Text matches are case-insensitive.",
        "input_schema": {
            "type": "object",
            "properties": {
                "table": {"type": "string", "enum": list(TABLES)},
                "filters": {"type": "array", "items": {"type": "object", "properties": {
                    "column": {"type": "string"},
                    "op": {"type": "string", "enum": ["=", "!=", ">", ">=", "<", "<=", "contains", "in", "between"]},
                    "value": {"description": "A value, a list for 'in', or [low, high] for 'between'. Dates as YYYY-MM-DD."}},
                    "required": ["column", "op", "value"]}},
                "group_by": {"type": "array", "items": {"type": "string"}},
                "metrics": {"type": "array", "items": {"type": "object", "properties": {
                    "column": {"type": "string"},
                    "agg": {"type": "string", "enum": ["count", "sum", "mean", "median", "min", "max", "nunique"]}},
                    "required": ["column", "agg"]},
                    "description": "Aggregations. Result columns are named <agg>_<column>, e.g. mean_delay_probability."},
                "columns": {"type": "array", "items": {"type": "string"}, "description": "Columns to return when not aggregating."},
                "sort_by": {"type": "string", "description": "Column to sort by (an original column, or <agg>_<column> after aggregating)."},
                "ascending": {"type": "boolean", "default": False},
                "limit": {"type": "integer", "default": 20, "maximum": 50},
            },
            "required": ["table"],
        },
    },
    {
        "name": "get_record",
        "description": "Look up one record by ID: an at-risk order (SO-12345), a shipment (ORD00001), a product (PRD0001), "
                       "or an associate's attendance summary (EMP101).",
        "input_schema": {"type": "object", "properties": {"record_id": {"type": "string"}}, "required": ["record_id"]},
    },
    {
        "name": "daily_snapshot",
        "description": "Summarize one date across all tables: at-risk orders released, labor attendance by status and zone, "
                       "and shipments expected to ship that day with delays.",
        "input_schema": {"type": "object", "properties": {"date": {"type": "string", "description": "YYYY-MM-DD"}},
                         "required": ["date"]},
    },
]


def run_tool(name, args):
    try:
        if name == "query_table":
            res = query_table(**args)
        elif name == "get_record":
            res = get_record(**args)
        elif name == "daily_snapshot":
            res = daily_snapshot(**args)
        else:
            res = {"error": f"unknown tool {name}"}
    except Exception as e:
        res = {"error": str(e)}
    return json.dumps(res, default=lambda x: x.item() if isinstance(x, np.generic) else str(x))
