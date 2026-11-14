# Warehouse Order Delay Prediction: Synthetic Source Data

Synthetic but internally consistent data for a distribution center operating Monday to Saturday, January 2025 to June 2026 (18 months, 44,991 orders, about 13% late). All tables link on shared keys so the full pipeline can be rebuilt: extract, label, point-in-time features, time split, train, explain.

## How the feeds connect

```
ERP  customers ──┐
ERP  materials ──┼──> ERP sales_orders ──> WMS order_lines ──> WMS pick_tasks ──> Carrier shipments
Carrier carriers ┘          │                     │                  │                   │
                            │          WMS inventory_snapshots   Labor clock_events      │
                            │          WMS zone_backlog_snapshots Labor employees        │
                            └──────────────> model/order_delay_features.csv <────────────┘ (label)
```

Keys: `order_id`, `customer_id`, `sku`, `employee_id` (= `picker_id`), `carrier_code`.

## 1. ERP feed (`erp/`)

| File | Rows | Columns |
|---|---|---|
| customers.csv | 600 | customer_id, customer_name, segment, sla_tier (Standard, Priority, Express), ship_to_state, late_penalty_usd |
| materials.csv | 1,500 | sku, description, primary_zone, unit_weight_lb, unit_price_usd, abc_class |
| sales_orders.csv | 44,991 | order_id, customer_id, order_created_ts, release_ts, required_ship_by_ts, carrier_code, priority (1 high to 3 low), order_channel, order_value_usd |

## 2. WMS feed (`wms/`)

| File | Rows | Columns |
|---|---|---|
| order_lines.csv | 435,955 | order_id, line_no, sku, qty_ordered, pick_zone (A to D), location_type (Primary, Reserve), bin_location |
| pick_tasks.csv | 435,955 | task_id, order_id, line_no, wave_id, picker_id, pick_zone, bin_location, location_type, qty_ordered, qty_picked, pick_start_ts, pick_confirm_ts, task_status (Confirmed, Short Pick) |
| zone_backlog_snapshots.csv | 13,224 | snapshot_ts (hourly), zone, open_orders, open_units, backlog_units_at_hour, zone_capacity_units, utilization_pct |
| inventory_snapshots.csv | 20,100 | snapshot_date (weekly), sku, zone, on_hand_primary, on_hand_reserve, min_primary_qty, replenishment_open |

Zones: A fast movers, B medium movers, C bulk or heavy (slowest, most reserve picks), D slow movers or cold.

## 3. Labor feed (`labor/`)

| File | Rows | Columns |
|---|---|---|
| employees.csv | 70 | employee_id, role (Picker, Packer, Lead), home_zone, hire_date, pick_rate_units_hr, employment_type |
| clock_events.csv | 13,630 | employee_id, work_date, clock_in_ts, clock_out_ts, assigned_zone, overtime_flag |

Mondays have lower staffing on purpose, and November and December are peak season, to reproduce the "large multi-zone order released late on a short-staffed Monday" scenario.

## 4. Carrier feed (`carrier/`)

| File | Rows | Columns |
|---|---|---|
| carriers.csv | 5 | carrier_code, carrier_name, service_level, daily_cutoff_time, pickup_window_min |
| shipments.csv | 44,991 | shipment_id, order_id, carrier_code, carrier_cutoff_ts, pack_complete_ts, actual_ship_ts, tracking_number, cartons, ship_weight_lb, ship_status, minutes_vs_cutoff |

Carrier cutoffs: UPS Ground 17:00, FedEx Ground 16:30, UPS 2nd Day 16:00, USPS Priority 15:00, Regional LTL 14:00. Orders released less than 30 minutes before cutoff roll to the next working day.

## 5. Modeling table (`model/order_delay_features.csv`)

One row per order, with features calculated **as of release_ts** (no future information), plus the label and a time-based split.

| Feature | Meaning | Source |
|---|---|---|
| sla_tier, priority, carrier_code, order_channel, order_value_usd | Order attributes | ERP |
| lines_count, units, zones_touched, dominant_zone | Order size and complexity | WMS |
| reserve_lines | Lines whose stock sits only in reserve at release | WMS inventory |
| zone_backlog_units | Units released into the dominant zone in the prior 3 hours | WMS |
| zone_backlog_ratio | zone_backlog_units divided by zone capacity | WMS |
| pickers_on_shift, zone_pickers_on_shift | Pickers clocked in at release time (total and in the dominant zone) | Labor |
| units_per_picker | units divided by pickers_on_shift | Labor plus WMS |
| hours_to_cutoff | Hours from release to carrier cutoff | ERP plus Carrier |
| release_hour, day_of_week, is_peak_season | Calendar context | Derived |
| **is_late** | 1 if actual_ship_ts is after carrier_cutoff_ts, otherwise 0 | Carrier |
| split | train (Jan to Dec 2025), validation (Jan to Mar 2026), test (Apr to Jun 2026) | Derived |

| Split | Orders | Late rate |
|---|---|---|
| train | 31,099 | 13.8% |
| validation | 6,819 | 12.2% |
| test | 7,073 | 10.9% |

## Built-in delay drivers

The label is drawn from a known risk function, so SHAP results should recover these drivers: low hours_to_cutoff, high zone_backlog_ratio, more lines and zones touched, reserve-location picks, fewer pickers on shift, Monday, peak season, zone C, and two interactions (backlog times short cutoff window, and LTL carrier times short cutoff window). A baseline gradient boosting model reaches about 0.81 ROC AUC on the test split.

