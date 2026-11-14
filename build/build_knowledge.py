"""
Builds knowledge/analytics_summary.md from the four data tables, so the retriever has
precomputed facts for the most common questions. Rerun after the data changes:
    python build/build_knowledge.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import data_store as ds  # noqa: E402

T = ds.TABLES
o, inv, sh, la = T["warehouse_orders"], T["inventory"], T["shipping_delays"], T["labor_attendance"]


def pct(x):
    return f"{x * 100:.1f}%"


def lines(series, fmt):
    return "\n".join(f"- {k}: {fmt(v)}" for k, v in series.items())


drivers = o.risk_drivers.str.split("; ").explode().value_counts()
pick = la[la.role == "Picker"]
daily_pickers = pick.groupby("date").is_present.sum()
orders_per_day = o.groupby("release_date").size()
joined = daily_pickers.to_frame("pickers_present").join(orders_per_day.rename("at_risk_orders")).fillna(0)
low_staff = joined.pickers_present <= joined.pickers_present.quantile(0.25)

delayed = sh[sh.is_delayed == 1]
staff_dates = set(delayed.loc[delayed.Delay_Reason == "Staffing constraints", "Expected_Ship_Date"])
att_staff = la[la.date.isin(staff_dates)].is_present.mean()

doc = f"""# Warehouse Analytics Summary

Precomputed facts from the four warehouse tables. For anything not listed here, the assistant queries the tables directly.

## At-risk orders overview
{len(o):,} orders flagged at risk between {o.release_ts.min():%B %d} and {o.release_ts.max():%B %d, %Y}. Average delay probability {o.delay_probability.mean():.2f}; {int((o.risk_tier == 'Critical').sum())} Critical (0.60 or higher), {int((o.risk_tier == 'High').sum())} High (0.40 to 0.60), {int((o.risk_tier == 'Elevated').sum())} Elevated (below 0.40).

## At-risk orders by zone
{lines(o.groupby('dominant_zone').delay_probability.agg(['size', 'mean']).apply(lambda r: f"{int(r['size'])} orders, average delay probability {r['mean']:.2f}", axis=1), str)}

## At-risk orders by month
{lines(o.groupby('release_month').size(), lambda v: f"{v} orders")}

## At-risk orders by day of week
{lines(o.groupby('day_of_week').size().sort_values(ascending=False), lambda v: f"{v} orders")}

## Most common risk drivers (SHAP)
{lines(drivers, lambda v: f"appears in {v} orders ({pct(v / len(o))})")}

## Most common suggested actions
{lines(o.suggested_action.value_counts().head(6), lambda v: f"{v} orders")}

## Shipping performance
{len(sh)} shipments, {int(sh.is_delayed.sum())} delayed ({pct(sh.is_delayed.mean())}), {len(sh) - int(sh.is_delayed.sum())} on time. Average delay among delayed shipments: {delayed.Delay_Days.mean():.1f} days; maximum {sh.Delay_Days.max()} days.

## Shipping delays by reason
{lines(delayed.groupby('Delay_Reason').Delay_Days.agg(['size', 'mean']).sort_values('size', ascending=False).apply(lambda r: f"{int(r['size'])} delayed shipments, average {r['mean']:.1f} days late", axis=1), str)}

## Shipping delay rate by carrier
{lines(sh.groupby('Carrier').is_delayed.agg(['size', 'mean']).apply(lambda r: f"{pct(r['mean'])} delayed ({int(r['size'])} shipments)", axis=1), str)}

## Shipping delay rate by month ordered
{lines(sh.groupby('order_month').is_delayed.agg(['size', 'mean']).apply(lambda r: f"{pct(r['mean'])} delayed ({int(r['size'])} shipments)", axis=1), str)}

## Inventory status
{len(inv)} products, {int((inv.Inventory_Status == 'Low Stock').sum())} Low Stock (at or below reorder level). Total stock value {inv.stock_value_usd.sum():,.0f} USD.
Low Stock items: {', '.join(f"{r.Product_ID} ({r.Category}, {r.Stock_Available} on hand vs reorder {r.Reorder_Level}, {r.Warehouse_Location})" for r in inv[inv.Inventory_Status == 'Low Stock'].sort_values('units_above_reorder').itertuples())}.

## Inventory by category
{lines(inv.groupby('Category').agg(products=('Product_ID', 'size'), units=('Stock_Available', 'sum'), low=('Inventory_Status', lambda s: (s == 'Low Stock').sum()), value=('stock_value_usd', 'sum')).apply(lambda r: f"{int(r.products)} products, {int(r.units):,} units, {int(r.low)} low stock, {r['value']:,.0f} USD", axis=1), str)}

## Labor attendance overview
60 associates (40 pickers, 10 packers, 6 forklift operators, 4 shift leads) over {la.date.nunique()} working days. Overall attendance rate {pct(la.is_present.mean())}; {int(la.is_absent.sum())} absences (including {int((la.status == 'No Call No Show').sum())} no call no shows), {int(la.is_late.sum())} late arrivals, {int((la.status == 'PTO').sum())} PTO days, {la.overtime_hours.sum():,.0f} overtime hours.

## Attendance rate by day of week
{lines(la.groupby('day_of_week').is_present.mean().sort_values(), pct)}

## Attendance rate by month
{lines(la.groupby('month').is_present.mean(), pct)}

## Attendance rate by role
{lines(la.groupby('role').is_present.mean().sort_values(), pct)}

## Attendance rate by employment type
{lines(la.groupby('employment_type').is_present.mean().sort_values(), pct)}

## Absence reasons
{lines(la[la.absence_reason != ''].absence_reason.value_counts(), lambda v: f"{v} days")}

## Labor and delays
- On the expected ship dates of shipments delayed for staffing constraints, attendance averaged {pct(att_staff)} versus {pct(la.is_present.mean())} overall.
- On the quarter of days with the fewest pickers present (at most {int(joined.pickers_present.quantile(0.25))} pickers), there were on average {joined[low_staff].at_risk_orders.mean():.1f} at-risk orders per day, versus {joined[~low_staff].at_risk_orders.mean():.1f} on better-staffed days.
- Mondays have the lowest attendance ({pct(la[la.day_of_week == 'Monday'].is_present.mean())}) and the most at-risk orders ({int((o.day_of_week == 'Monday').sum())}), matching the Monday staffing pattern risk driver.
"""
out = Path(__file__).resolve().parents[1] / "knowledge/analytics_summary.md"
out.write_text(doc)
print(doc)
