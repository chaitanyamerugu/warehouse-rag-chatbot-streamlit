# Warehouse Analytics Summary

Precomputed facts from the four warehouse tables. For anything not listed here, the assistant queries the tables directly.

## At-risk orders overview
2,000 orders flagged at risk between July 01 and November 13, 2026. Average delay probability 0.45; 302 Critical (0.60 or higher), 777 High (0.40 to 0.60), 921 Elevated (below 0.40).

## At-risk orders by zone
- A: 1421 orders, average delay probability 0.46
- B: 449 orders, average delay probability 0.42
- C: 108 orders, average delay probability 0.39
- D: 22 orders, average delay probability 0.39

## At-risk orders by month
- 2026-07: 425 orders
- 2026-08: 480 orders
- 2026-09: 433 orders
- 2026-10: 461 orders
- 2026-11: 201 orders

## At-risk orders by day of week
- Monday: 696 orders
- Friday: 305 orders
- Saturday: 301 orders
- Thursday: 258 orders
- Tuesday: 234 orders
- Wednesday: 206 orders

## Most common risk drivers (SHAP)
- items only in reserve locations: appears in 1276 orders (63.8%)
- high backlog in its zone: appears in 1057 orders (52.8%)
- high units per available picker: appears in 959 orders (47.9%)
- items spread across several zones: appears in 514 orders (25.7%)
- little time to carrier cutoff: appears in 481 orders (24.1%)
- Monday staffing pattern: appears in 284 orders (14.2%)
- large unit count: appears in 172 orders (8.6%)
- few pickers on shift: appears in 165 orders (8.2%)
- zone C workload: appears in 105 orders (5.2%)

## Most common suggested actions
- Add 2 pickers to zone A; trigger replenishment from reserve now: 465 orders
- Add 2 pickers to zone A; trigger replenishment from reserve now; split the shipment if the customer allows: 319 orders
- Add 2 pickers to zone A: 178 orders
- Add 2 pickers to zone B; trigger replenishment from reserve now: 135 orders
- Trigger replenishment from reserve now; split the shipment if the customer allows: 121 orders
- Move to the next pick wave now; add 2 pickers to zone A; trigger replenishment from reserve now: 102 orders

## Shipping performance
200 shipments, 54 delayed (27.0%), 146 on time. Average delay among delayed shipments: 2.6 days; maximum 4 days.

## Shipping delays by reason
- Carrier capacity: 17 delayed shipments, average 2.3 days late
- High order volume: 11 delayed shipments, average 2.9 days late
- Equipment downtime: 10 delayed shipments, average 2.8 days late
- Staffing constraints: 9 delayed shipments, average 2.4 days late
- Inventory shortage: 7 delayed shipments, average 2.6 days late

## Shipping delay rate by carrier
- Carrier A: 31.6% delayed (57 shipments)
- Carrier B: 30.4% delayed (69 shipments)
- Carrier C: 20.3% delayed (74 shipments)

## Shipping delay rate by month ordered
- 2026-09: 28.6% delayed (91 shipments)
- 2026-10: 26.3% delayed (95 shipments)
- 2026-11: 21.4% delayed (14 shipments)

## Inventory status
100 products, 10 Low Stock (at or below reorder level). Total stock value 1,435,759 USD.
Low Stock items: PRD0055 (Office Supplies, 16 on hand vs reorder 40, A3-R15), PRD0035 (Home Goods, 5 on hand vs reorder 20, A2-R15), PRD0068 (Apparel, 7 on hand vs reorder 20, A4-R08), PRD0066 (Apparel, 38 on hand vs reorder 50, A4-R06), PRD0076 (Apparel, 31 on hand vs reorder 40, A4-R16), PRD0052 (Office Supplies, 32 on hand vs reorder 40, A3-R12), PRD0004 (Electronics, 16 on hand vs reorder 20, A1-R04), PRD0023 (Home Goods, 28 on hand vs reorder 30, A2-R03), PRD0054 (Office Supplies, 30 on hand vs reorder 30, A3-R14), PRD0071 (Apparel, 30 on hand vs reorder 30, A4-R11).

## Inventory by category
- Apparel: 20 products, 2,625 units, 4 low stock, 292,421 USD
- Electronics: 20 products, 2,017 units, 1 low stock, 234,749 USD
- Hardware: 20 products, 2,643 units, 0 low stock, 279,318 USD
- Home Goods: 20 products, 2,815 units, 2 low stock, 312,746 USD
- Office Supplies: 20 products, 2,871 units, 3 low stock, 316,525 USD

## Labor attendance overview
60 associates (40 pickers, 10 packers, 6 forklift operators, 4 shift leads) over 118 working days. Overall attendance rate 84.7%; 916 absences (including 162 no call no shows), 419 late arrivals, 167 PTO days, 1,770 overtime hours.

## Attendance rate by day of week
- Monday: 78.7%
- Saturday: 79.6%
- Friday: 83.5%
- Tuesday: 88.3%
- Thursday: 88.5%
- Wednesday: 89.5%

## Attendance rate by month
- 2026-07: 86.4%
- 2026-08: 85.6%
- 2026-09: 84.2%
- 2026-10: 82.8%
- 2026-11: 84.2%

## Attendance rate by role
- Forklift Operator: 79.7%
- Shift Lead: 81.6%
- Packer: 82.1%
- Picker: 86.4%

## Attendance rate by employment type
- Temp: 79.0%
- Part-time: 85.7%
- Full-time: 86.3%

## Absence reasons
- Sick: 398 days
- Personal: 205 days
- PTO: 167 days
- Unexcused: 162 days
- Transportation: 151 days

## Labor and delays
- On the expected ship dates of shipments delayed for staffing constraints, attendance averaged 75.9% versus 84.7% overall.
- On the quarter of days with the fewest pickers present (at most 33 pickers), there were on average 23.3 at-risk orders per day, versus 14.4 on better-staffed days.
- Mondays have the lowest attendance (78.7%) and the most at-risk orders (696), matching the Monday staffing pattern risk driver.
