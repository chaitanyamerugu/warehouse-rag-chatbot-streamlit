# Data Dictionary

## warehouse_orders (data/warehouse_orders.csv, 2,000 rows)
Orders flagged at risk of missing their carrier cutoff, July 1 to November 13, 2026. Every row is above the alert threshold (delay probability 0.28 or higher).
- order_id: order number, SO-93004 to SO-99997
- release_ts: date and time the order was released to the warehouse floor
- required_ship_by_ts: carrier cutoff the order must ship by
- dominant_zone: picking zone holding most of the order's units (A, B, C, D)
- lines_count: number of order lines (1 to 80)
- pickers_on_shift: pickers clocked in when the order was released
- hours_to_cutoff: hours between release and the carrier cutoff
- delay_probability: model probability that the order ships late (0.28 to 0.87)
- risk_drivers: top SHAP factors raising the risk, separated by semicolons
- suggested_action: recommended supervisor response
- Derived in the app: release_date, release_month, day_of_week, risk_tier (Critical 0.60 or higher, High 0.40 to 0.60, Elevated below 0.40)

## inventory (data/inventory.csv, 100 rows)
- Product_ID: PRD0001 to PRD0100
- Product_Name, Category: Electronics, Home Goods, Office Supplies, Apparel, Hardware (20 products each)
- Stock_Available: units on hand
- Reorder_Level: reorder point; at or below it the product is Low Stock
- Warehouse_Location: aisle and rack, for example A3-R15 (aisle A3, rack 15)
- Unit_Price_USD, Inventory_Status (In Stock, Low Stock)
- Derived in the app: units_above_reorder, stock_value_usd, aisle

## shipping_delays (data/shipping_delays.csv, 200 rows)
- Order_ID: ORD00001 to ORD00200
- Order_Date, Expected_Ship_Date, Actual_Ship_Date
- Delivery_Status: On Time or Delayed
- Delay_Days: days shipped after the expected date (0 to 4)
- Delay_Reason: Carrier capacity, High order volume, Equipment downtime, Staffing constraints, Inventory shortage, or None
- Carrier: Carrier A, Carrier B, Carrier C
- Derived in the app: order_month, expected_ship_weekday, is_delayed (1 or 0)

## labor_attendance (data/labor_attendance.csv, 7,080 rows)
Daily attendance for 60 associates, July 1 to November 14, 2026, Monday to Saturday (the warehouse is closed Sundays). One row per associate per working day.
- date, day_of_week
- employee_id (EMP101 to EMP160), employee_name
- role: Picker (40), Packer (10), Forklift Operator (6), Shift Lead (4)
- assigned_zone: A, B, C, D
- shift: Day (starts 06:00) or Mid (starts 10:00)
- employment_type: Full-time, Part-time (6 hour shifts), Temp
- scheduled_hours, hours_worked, overtime_hours
- status: Present, Late (10 or more minutes late), Absent, No Call No Show, PTO
- clock_in, clock_out (blank when not present), minutes_late
- absence_reason: Sick, Personal, Transportation, Unexcused, PTO, or blank
- Derived in the app: month, is_present, is_absent, is_late
- Generation rules: Monday and Saturday attendance is lower; attendance drops on the expected ship dates of shipments delayed for staffing constraints; each day has at least as many pickers present as the highest pickers_on_shift recorded in warehouse_orders that day.

## How the tables relate
- warehouse_orders and labor_attendance share dates and zones: compare at-risk orders per day with pickers present per day and zone.
- shipping_delays and labor_attendance share dates: staffing constraint delays line up with low attendance on the expected ship date.
- inventory supports the "items only in reserve locations" and "inventory shortage" findings: Low Stock products need replenishment.
