# Supervisor Operations Playbook for At-Risk Orders

## When an order is flagged high risk
An order is flagged high risk when its predicted delay probability is at or above the alert threshold, which is set to flag about the top 10% riskiest orders so the alert volume matches what supervisors can act on in a shift. High-risk orders appear on the supervisor dashboard ranked by risk and by time remaining to carrier cutoff. The supervisor reviews the SHAP drivers for the order and chooses one or more of the responses below. The model recommends; the supervisor decides.

## Response: move the order to the next pick wave
Use when the main driver is little time to carrier cutoff. Waves release roughly every two hours. Moving a high-risk order to the front of the next wave, or releasing it as a hot pick immediately, buys the most time. Confirm the pack station has capacity for the order before moving it.

## Response: reassign pickers to the backed-up zone
Use when the drivers include high backlog in its zone, few pickers in its zone, or high units per available picker. Move two pickers from the zone with the lowest utilization in the latest hourly backlog snapshot. Zone D (slow movers and cold storage) usually has spare capacity. Cross-trained pickers keep their pick rate; temporary staff should be paired with a lead.

## Response: trigger replenishment from reserve
Use when the drivers include items only in reserve locations. Reserve picks take 20 to 75 extra minutes because a forklift driver must bring stock down from reserve racking. Create an emergency replenishment task as soon as the order is released, not when the picker reaches an empty bin.

## Response: split the shipment
Use for large orders (25 or more lines) touching three or more zones when the cutoff cannot be met for the whole order. Ship the lines that are ready and send the remainder on the next pickup. Check the customer's split-shipment permission in the ERP first. Wholesale customers usually allow splits; some marketplace accounts do not.

## Response: contact the carrier
Use for Regional LTL Freight (LTLX) orders when hours to cutoff is under three. LTLX has the earliest cutoff (14:00) and a 60 minute pickup window. The transportation coordinator can request a late pickup or move the freight to a later trailer.

## Response: notify the customer or account team
Use for Express SLA customers when the order is still likely to miss after the steps above. Express customers carry a 150 USD late penalty per order, Priority 75 USD, and Standard 25 USD. Early notification often avoids the chargeback.

## Common risk patterns
- Large multi-zone orders released on a short-staffed Monday are the highest-risk combination. Monday attendance is the lowest of the week (about 79% versus about 89% midweek) and Monday has the most at-risk orders.
- Items stored only in reserve locations is the most common risk driver, so replenishment timing matters more than any other single lever.
- Zone A carries most at-risk orders; reassign pickers into zone A first when it is backed up.
- Temporary associates have lower attendance (about 79%) than full-time associates (about 86%). Pair temps with a lead and plan for absences.

## Response: low stock and inventory shortage
When a product is at or below its reorder level (Low Stock), raise a purchase or replenishment request the same day and check open at-risk orders that need it. Inventory shortage caused 7 of the 54 delayed shipments. Products at zero buffer (stock equal to the reorder level) should be treated as Low Stock.

## Response: carrier capacity problems
Carrier capacity is the most common shipping delay reason. When a carrier is short on capacity, book overflow loads with another carrier early in the day, and compare carrier delay rates before assigning priority shipments. Carrier C has the lowest delay rate in the shipping data.

## Response: equipment downtime
Equipment downtime delays average almost three days. Report forklift or conveyor faults to maintenance immediately, move forklift operators to manual replenishment tasks, and reprioritize waves around the affected zone.

## Response: staffing constraints and absences
When attendance drops below about 80% or a zone is short, call in part-time associates, approve overtime for present staff, move cross-trained packers to picking, and hold low-priority waves. Check the labor attendance table for no call no shows early in the shift so gaps are filled before the first wave.

## Escalation
If more than 15 orders are flagged high risk within one hour, the shift supervisor should notify the operations manager and consider authorizing overtime for the current shift.
