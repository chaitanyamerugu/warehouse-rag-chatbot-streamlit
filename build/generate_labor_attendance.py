"""
Generate daily labor attendance that lines up with the project's sample data:
  - same date range as warehouse_orders.csv (July 1 to November 14, 2026), Monday to Saturday
  - enough pickers present each day to cover the highest pickers_on_shift recorded in warehouse_orders.csv
  - lower attendance on Mondays (matches the "Monday staffing pattern" risk driver)
  - extra absences on the expected ship dates of shipments delayed for "Staffing constraints"
Usage: python build/generate_labor_attendance.py data
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(7)
DATA = Path(sys.argv[1] if len(sys.argv) > 1 else "data")

orders = pd.read_csv(DATA / "warehouse_orders.csv", parse_dates=["release_ts"])
ship = pd.read_csv(DATA / "shipping_delays.csv", parse_dates=["Expected_Ship_Date"])

# ---------------- roster ----------------
roles = (["Picker"] * 40) + (["Packer"] * 10) + (["Forklift Operator"] * 6) + (["Shift Lead"] * 4)
zones = np.r_[rng.choice(["A", "B", "C", "D"], 40, p=[.5, .25, .15, .10]),
              rng.choice(["A", "B", "C", "D"], 20)]
shifts = np.where(rng.random(60) < 0.7, "Day", "Mid")
emp_type = rng.choice(["Full-time", "Part-time", "Temp"], 60, p=[.65, .2, .15])
roster = pd.DataFrame({
    "employee_id": [f"EMP{101 + i:03d}" for i in range(60)],
    "employee_name": [f"Associate {101 + i:03d}" for i in range(60)],
    "role": roles, "assigned_zone": zones, "shift": shifts, "employment_type": emp_type,
    "reliability": np.clip(rng.normal(0.0, 0.05, 60), -0.12, 0.08),
})
roster.loc[roster.employment_type == "Temp", "reliability"] -= 0.06
SHIFT_START = {"Day": 6.0, "Mid": 10.0}

# ---------------- daily attendance ----------------
days = [d for d in pd.date_range("2026-07-01", "2026-11-14") if d.dayofweek != 6]
need = orders.groupby(orders.release_ts.dt.normalize()).pickers_on_shift.max()
staffing_days = set(ship.loc[ship.Delay_Reason == "Staffing constraints", "Expected_Ship_Date"].dt.normalize())
staffing_days |= {d - pd.Timedelta(days=1) for d in staffing_days}

rows = []
for d in days:
    base = {0: 0.76, 1: 0.90, 2: 0.91, 3: 0.90, 4: 0.86, 5: 0.82}[d.dayofweek]
    if d in staffing_days:
        base -= 0.12
    p = np.clip(base + roster.reliability.values, 0.4, 0.98)
    present = rng.random(60) < p
    # guarantee enough pickers to match the highest pickers_on_shift recorded that day
    pick_idx = np.where(roster.role == "Picker")[0]
    required = int(need.get(d, 0))
    short = required - present[pick_idx].sum()
    if short > 0:
        absent_pickers = pick_idx[~present[pick_idx]]
        present[rng.choice(absent_pickers, short, replace=False)] = True
    for i, e in roster.iterrows():
        start_h = SHIFT_START[e["shift"]]
        sched = 8.0 if e.employment_type != "Part-time" else 6.0
        rec = {"date": d.date(), "day_of_week": d.day_name(), "employee_id": e.employee_id,
               "employee_name": e.employee_name, "role": e.role, "assigned_zone": e.assigned_zone,
               "shift": e["shift"], "employment_type": e.employment_type, "scheduled_hours": sched}
        if present[i]:
            late_min = int(rng.integers(10, 45)) if rng.random() < 0.06 else int(rng.choice([0, 0, 0, 3, 5]))
            if d.dayofweek == 0 and rng.random() < 0.08:
                late_min = int(rng.integers(15, 60))
            cin = d + pd.Timedelta(hours=start_h, minutes=late_min - int(rng.integers(0, 8)))
            ot = float(rng.choice([0, 0, 0, 0, 0.5, 1, 2])) if (d.month in (10, 11) or d.dayofweek == 0) else float(rng.choice([0, 0, 0, 0, 0, 0, 1]))
            worked = round(sched - max(late_min, 0) / 60 + ot, 2)
            cout = cin + pd.Timedelta(hours=worked + 0.5)  # 30 min unpaid lunch
            rec.update(status="Late" if late_min >= 10 else "Present", clock_in=cin.strftime("%H:%M"),
                       clock_out=cout.strftime("%H:%M"), hours_worked=worked, overtime_hours=ot,
                       minutes_late=late_min if late_min >= 10 else 0, absence_reason="")
        else:
            reason = rng.choice(["Sick", "Personal", "Transportation", "Unexcused", "PTO"], p=[.35, .2, .15, .15, .15])
            rec.update(status="PTO" if reason == "PTO" else ("No Call No Show" if reason == "Unexcused" else "Absent"),
                       clock_in="", clock_out="", hours_worked=0.0, overtime_hours=0.0, minutes_late=0,
                       absence_reason=reason)
        rows.append(rec)

att = pd.DataFrame(rows)
att.to_csv(DATA / "labor_attendance.csv", index=False)
print(att.shape)
print(att.status.value_counts().to_dict())
att["present"] = att.status.isin(["Present", "Late"])
print("attendance rate by weekday:", att.groupby("day_of_week").present.mean().round(3).to_dict())
pk = att[(att.role == "Picker") & att.present].groupby("date").size()
pk.index = pd.to_datetime(pk.index)
chk = pd.concat([pk.rename("present"), need.rename("need")], axis=1).dropna()
print("days where present pickers < max pickers_on_shift:", int((chk.present < chk.need).sum()))
sd = att[pd.to_datetime(att.date).isin(staffing_days)].present.mean()
print("attendance on staffing-constraint days:", round(sd, 3), "overall:", round(att.present.mean(), 3))
