# Warehouse Delay Analytics Summary

Data covers January 01, 2025 to June 30, 2026: 44,991 orders, 13.1% shipped after the carrier cutoff.

## Late rate by picking zone
- A: 17.6% late (19,347 orders)
- B: 11.1% late (14,151 orders)
- C: 10.0% late (7,017 orders)
- D: 4.5% late (4,476 orders)

## Late rate by day of week
- Monday: 19.1% late (8,969 orders)
- Saturday: 14.7% late (7,177 orders)
- Wednesday: 11.3% late (7,313 orders)
- Friday: 11.0% late (7,259 orders)
- Tuesday: 10.9% late (7,193 orders)
- Thursday: 10.2% late (7,080 orders)

## Late rate by carrier
- LTLX: 15.7% late (4,040 orders)
- USPS: 14.0% late (7,218 orders)
- UPS2D: 13.1% late (3,937 orders)
- FDXG: 12.9% late (10,600 orders)
- UPSG: 12.3% late (19,196 orders)

## Late rate by SLA tier
- Priority: 13.1% late (14,266 orders)
- Express: 13.1% late (3,937 orders)
- Standard: 13.1% late (26,788 orders)

## Late rate by hours to cutoff at release
- under 2 h: 25.9% late (1,830 orders)
- 2 to 4 h: 13.9% late (5,740 orders)
- over 8 h: 13.8% late (23,091 orders)
- 4 to 8 h: 10.0% late (14,330 orders)

## Late rate by order size
- over 30 lines: 47.3% late (1,669 orders)
- 16 to 30 lines: 23.7% late (5,852 orders)
- 6 to 15 lines: 13.2% late (19,606 orders)
- 1 to 5 lines: 6.3% late (17,864 orders)

## Late rate by pickers on shift at release
- 25 or fewer pickers: 14.7% late (28,330 orders)
- more than 35 pickers: 11.0% late (1,540 orders)
- 26 to 35 pickers: 10.2% late (15,121 orders)

## Late rate by month
- 2025-12: 21.8% late (3,782 orders)
- 2025-11: 19.9% late (3,443 orders)
- 2025-08: 13.9% late (2,776 orders)
- 2026-03: 12.9% late (2,365 orders)
- 2025-01: 12.5% late (2,338 orders)
- 2026-01: 12.1% late (2,267 orders)
- 2025-05: 11.9% late (2,430 orders)
- 2025-03: 11.8% late (2,279 orders)
- 2025-07: 11.7% late (2,790 orders)
- 2026-02: 11.7% late (2,187 orders)
- 2025-06: 11.5% late (2,183 orders)
- 2025-10: 11.3% late (2,429 orders)
- 2026-05: 11.1% late (2,363 orders)
- 2026-06: 11.1% late (2,371 orders)
- 2025-09: 10.8% late (2,278 orders)
- 2025-04: 10.5% late (2,306 orders)
- 2026-04: 10.4% late (2,339 orders)
- 2025-02: 9.8% late (2,065 orders)

## Carrier cutoffs
- UPSG (UPS Ground, Ground): daily cutoff 17:00, pickup window 30 min
- FDXG (FedEx Ground, Ground): daily cutoff 16:30, pickup window 30 min
- USPS (USPS Priority, Priority): daily cutoff 15:00, pickup window 20 min
- LTLX (Regional LTL Freight, LTL): daily cutoff 14:00, pickup window 60 min
- UPS2D (UPS 2nd Day Air, Express): daily cutoff 16:00, pickup window 20 min

## Delay prediction model performance
The XGBoost model was trained on 2025 orders, tuned on January to March 2026, and tested on April to June 2026 (7,073 orders).
- ROC AUC on test: 0.815
- Precision recall AUC on test: 0.427
- Alert threshold: delay probability of 0.28 or higher, which flags about the top 10% riskiest orders (9.5% of test orders flagged)
- At that threshold, precision is 45.2% (share of flagged orders that really shipped late) and recall is 39.6% (share of late orders that were flagged)

## Global feature importance (mean absolute SHAP value)
1. items only in reserve locations (reserve_lines): 0.400
2. high backlog in its zone (zone_backlog_ratio): 0.295
3. high backlog in its zone (zone_backlog_units): 0.271
4. high units per available picker (units_per_picker): 0.230
5. items spread across several zones (zones_touched): 0.189
6. few pickers on shift (pickers_on_shift): 0.167
7. little time to carrier cutoff (hours_to_cutoff): 0.157
8. day of week (day_of_week): 0.093
9. peak season volume (is_peak_season): 0.090
10. zone (dominant_zone): 0.075
11. many order lines (lines_count): 0.023
12. large unit count (units): 0.022
13. few pickers in its zone (zone_pickers_on_shift): 0.021
14. order value (order_value_usd): 0.017
15. carrier (carrier_code): 0.014
16. late release hour (release_hour): 0.006
17. order channel (order_channel): 0.005
18. SLA tier (sla_tier): 0.002
19. order priority (priority): 0.000