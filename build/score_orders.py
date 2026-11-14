"""
Train the delay model and produce the artifacts the chatbot retrieves from:
  data/scored_orders.csv      test-period orders with delay probability, SHAP drivers, suggested action
  knowledge/*.md              analytics summary generated from the data
"""
import sys
import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from pathlib import Path
from sklearn.metrics import roc_auc_score, average_precision_score, precision_score, recall_score

SRC = Path(sys.argv[1])            # wms_dataset folder
OUT = Path(sys.argv[2])            # space folder
(OUT / "data").mkdir(parents=True, exist_ok=True)
(OUT / "knowledge").mkdir(parents=True, exist_ok=True)

m = pd.read_csv(SRC / "model/order_delay_features.csv", parse_dates=["release_ts"])
orders = pd.read_csv(SRC / "erp/sales_orders.csv", parse_dates=["required_ship_by_ts"])
ship = pd.read_csv(SRC / "carrier/shipments.csv", parse_dates=["actual_ship_ts"])
cust = pd.read_csv(SRC / "erp/customers.csv")
carriers = pd.read_csv(SRC / "carrier/carriers.csv")

FEATS = ["sla_tier", "carrier_code", "priority", "order_channel", "order_value_usd", "lines_count", "units",
         "zones_touched", "dominant_zone", "reserve_lines", "zone_backlog_units", "zone_backlog_ratio",
         "pickers_on_shift", "zone_pickers_on_shift", "units_per_picker", "hours_to_cutoff", "release_hour",
         "day_of_week", "is_peak_season"]
CATS = ["sla_tier", "carrier_code", "order_channel", "dominant_zone", "day_of_week"]
X = m[FEATS].copy()
for c in CATS:
    X[c] = X[c].astype("category")

tr, va, te = (m.split == s for s in ["train", "validation", "test"])
clf = xgb.XGBClassifier(n_estimators=400, learning_rate=0.05, max_depth=4, subsample=0.8, colsample_bytree=0.8,
                        enable_categorical=True, tree_method="hist", eval_metric="aucpr",
                        early_stopping_rounds=40, random_state=42)
clf.fit(X[tr], m.is_late[tr], eval_set=[(X[va], m.is_late[va])], verbose=False)

p_val = clf.predict_proba(X[va])[:, 1]
threshold = float(np.quantile(p_val, 0.90))       # flag top 10% riskiest, matching supervisor capacity
p_te = clf.predict_proba(X[te])[:, 1]
y_te = m.is_late[te]
flag = p_te >= threshold
metrics = {
    "auc": roc_auc_score(y_te, p_te), "pr_auc": average_precision_score(y_te, p_te),
    "precision": precision_score(y_te, flag), "recall": recall_score(y_te, flag),
    "threshold": threshold, "flag_rate": flag.mean(), "best_iter": clf.best_iteration,
}
print(metrics)

# ---- SHAP for test orders ----
expl = shap.TreeExplainer(clf)
sv = expl.shap_values(X[te])
LABEL = {
    "hours_to_cutoff": "little time to carrier cutoff", "zone_backlog_ratio": "high backlog in its zone",
    "zone_backlog_units": "high backlog in its zone", "lines_count": "many order lines",
    "units": "large unit count", "zones_touched": "items spread across several zones",
    "reserve_lines": "items only in reserve locations", "pickers_on_shift": "few pickers on shift",
    "zone_pickers_on_shift": "few pickers in its zone", "units_per_picker": "high units per available picker",
    "day_of_week": "day of week", "is_peak_season": "peak season volume", "dominant_zone": "zone",
    "carrier_code": "carrier", "release_hour": "late release hour", "sla_tier": "SLA tier",
    "priority": "order priority", "order_channel": "order channel", "order_value_usd": "order value",
}
te_df = m[te].reset_index(drop=True).copy()
te_df["delay_probability"] = p_te.round(3)
drivers_up, drivers_down = [], []
for i in range(len(te_df)):
    row = sv[i]
    idx = np.argsort(-row)
    up = []
    for j in idx[:3]:
        if row[j] > 0.15:
            f = FEATS[j]
            lab = LABEL[f]
            if f == "dominant_zone": lab = f"zone {te_df.dominant_zone[i]} workload"
            if f == "day_of_week": lab = f"{te_df.day_of_week[i]} staffing pattern"
            if f == "carrier_code": lab = f"carrier {te_df.carrier_code[i]} early cutoff"
            if lab not in up: up.append(lab)
    down = []
    for j in np.argsort(row)[:2]:
        if row[j] < -0.15:
            f = FEATS[j]
            lab = {"hours_to_cutoff": "plenty of time to cutoff", "pickers_on_shift": "good staffing",
                   "zone_backlog_ratio": "low zone backlog", "lines_count": "small order",
                   "reserve_lines": "stock in primary locations", "zones_touched": "single-zone order",
                   "units": "small unit count", "units_per_picker": "low units per picker"}.get(f, LABEL[f])
            down.append(lab)
    drivers_up.append("; ".join(up) if up else "none significant")
    drivers_down.append("; ".join(down) if down else "none significant")
te_df["risk_drivers"] = drivers_up
te_df["protective_factors"] = drivers_down


def action(r):
    if r.delay_probability < threshold:
        return "No action needed"
    acts = []
    if r.hours_to_cutoff < 3:
        acts.append("move to the next pick wave now")
    if r.zone_backlog_ratio > 0.5 or r.zone_pickers_on_shift <= 2:
        acts.append(f"add 2 pickers to zone {r.dominant_zone}")
    if r.reserve_lines > 0:
        acts.append("trigger replenishment from reserve now")
    if r.zones_touched >= 3 and r.lines_count >= 25:
        acts.append("split the shipment if the customer allows")
    if r.carrier_code == "LTLX" and r.hours_to_cutoff < 3:
        acts.append("call the LTL carrier to confirm a late pickup")
    if not acts:
        acts.append("monitor and prioritize in the current wave")
    if r.sla_tier == "Express":
        acts.append("notify the account team (Express SLA)")
    s = "; ".join(acts)
    return s[0].upper() + s[1:]


te_df["suggested_action"] = te_df.apply(action, axis=1)
te_df["risk_level"] = np.select([te_df.delay_probability >= threshold, te_df.delay_probability >= threshold / 2],
                                ["High", "Medium"], "Low")
te_df = te_df.merge(orders[["order_id", "required_ship_by_ts"]], on="order_id") \
             .merge(ship[["order_id", "actual_ship_ts"]], on="order_id")
keep = ["order_id", "release_ts", "required_ship_by_ts", "customer_id", "sla_tier", "carrier_code", "priority",
        "lines_count", "units", "zones_touched", "dominant_zone", "reserve_lines", "zone_backlog_ratio",
        "pickers_on_shift", "zone_pickers_on_shift", "units_per_picker", "hours_to_cutoff", "day_of_week",
        "delay_probability", "risk_level", "risk_drivers", "protective_factors", "suggested_action",
        "actual_ship_ts", "is_late"]
te_df[keep].to_csv(OUT / "data/scored_orders.csv", index=False, date_format="%Y-%m-%d %H:%M")

# ---- Global importance ----
imp = pd.Series(np.abs(sv).mean(0), index=FEATS).sort_values(ascending=False)

# ---- Analytics knowledge doc ----
full = m.merge(ship[["order_id", "actual_ship_ts"]], on="order_id")
def rate(col):
    g = full.groupby(col).is_late.agg(["size", "mean"]).sort_values("mean", ascending=False)
    return "\n".join(f"- {k}: {v['mean']*100:.1f}% late ({int(v['size']):,} orders)" for k, v in g.iterrows())

full["month"] = full.release_ts.dt.strftime("%Y-%m")
full["cutoff_band"] = pd.cut(full.hours_to_cutoff, [-1, 2, 4, 8, 1000], labels=["under 2 h", "2 to 4 h", "4 to 8 h", "over 8 h"])
full["size_band"] = pd.cut(full.lines_count, [0, 5, 15, 30, 100], labels=["1 to 5 lines", "6 to 15 lines", "16 to 30 lines", "over 30 lines"])
full["staff_band"] = pd.cut(full.pickers_on_shift, [-1, 25, 35, 100], labels=["25 or fewer pickers", "26 to 35 pickers", "more than 35 pickers"])

carrier_lines = "\n".join(f"- {r.carrier_code} ({r.carrier_name}, {r.service_level}): daily cutoff {r.daily_cutoff_time}, pickup window {r.pickup_window_min} min"
                          for r in carriers.itertuples())
doc = f"""# Warehouse Delay Analytics Summary

Data covers {full.release_ts.min():%B %d, %Y} to {full.release_ts.max():%B %d, %Y}: {len(full):,} orders, {full.is_late.mean()*100:.1f}% shipped after the carrier cutoff.

## Late rate by picking zone
{rate('dominant_zone')}

## Late rate by day of week
{rate('day_of_week')}

## Late rate by carrier
{rate('carrier_code')}

## Late rate by SLA tier
{rate('sla_tier')}

## Late rate by hours to cutoff at release
{rate('cutoff_band')}

## Late rate by order size
{rate('size_band')}

## Late rate by pickers on shift at release
{rate('staff_band')}

## Late rate by month
{rate('month')}

## Carrier cutoffs
{carrier_lines}

## Delay prediction model performance
The XGBoost model was trained on 2025 orders, tuned on January to March 2026, and tested on April to June 2026 ({te.sum():,} orders).
- ROC AUC on test: {metrics['auc']:.3f}
- Precision recall AUC on test: {metrics['pr_auc']:.3f}
- Alert threshold: delay probability of {threshold:.2f} or higher, which flags about the top 10% riskiest orders ({metrics['flag_rate']*100:.1f}% of test orders flagged)
- At that threshold, precision is {metrics['precision']*100:.1f}% (share of flagged orders that really shipped late) and recall is {metrics['recall']*100:.1f}% (share of late orders that were flagged)

## Global feature importance (mean absolute SHAP value)
""" + "\n".join(f"{i+1}. {LABEL.get(f, f)} ({f}): {v:.3f}" for i, (f, v) in enumerate(imp.items()))

(OUT / "knowledge/analytics_summary.md").write_text(doc)
print(te_df.risk_level.value_counts())
print(te_df.sort_values("delay_probability", ascending=False)[["order_id", "delay_probability", "risk_drivers", "suggested_action"]].head(5).to_string())
