# Warehouse Order Delay Prediction: Solution Overview

## Business problem
Warehouses need to know which customer orders are likely to miss their shipping deadline while there is still time to act. Distribution centers and e-commerce businesses process orders under fluctuating demand, limited labor, uneven inventory availability, and fixed carrier cutoffs. Late orders drive overtime, expedited freight, SLA chargebacks, lower customer satisfaction, and end-of-day pressure on frontline workers. Most warehouse management systems rely on predefined rules, order priorities, and end-of-shift reports, so supervisors often learn an order is late only after the cutoff has passed.

## Prediction task
For each new order, the model estimates the probability that it will ship after its required carrier cutoff. This is a binary classification task: an order is labeled late (1) if the actual ship timestamp is after the carrier cutoff, otherwise on time (0).

## How it is used
1. When an order is released, the model scores its delay probability using only information available at that moment.
2. Orders above the risk threshold appear on a supervisor dashboard ranked by risk and time to cutoff.
3. SHAP values show the top factors behind each score, such as zone backlog or items only in reserve locations (Lundberg and Lee, 2017).
4. Supervisors decide the response: reassign pickers, move the order up a wave, trigger replenishment, split the shipment, or contact the customer.

## Model development pipeline
1. Extract data: 18 months of order headers, pick tasks, labor clock-ins, inventory snapshots, and shipment confirmations from the WMS and ERP.
2. Create the label from carrier shipment timestamps compared with the cutoff.
3. Build point-in-time features exactly as they looked at release time, so no future information leaks into training.
4. Engineer ratios a supervisor would recognize: units per available picker, zone backlog divided by zone capacity, hours to cutoff.
5. Split by time: train on 2025, validate on January to March 2026, test on April to June 2026.
6. Train and tune XGBoost, compared against logistic regression, a single decision tree, and Random Forest.
7. Pick the alert threshold that flags about the top 10% riskiest orders.
8. Review global and individual SHAP explanations with operations leads before go-live.

## Why XGBoost
XGBoost builds many shallow decision trees in sequence, each correcting the errors of the trees before it (Chen and Guestrin, 2016). It captures interactions such as high backlog combined with a short time to cutoff, handles mixed numeric and categorical data and missing values, supports class weighting for the minority late class, and works with SHAP for explanations.

## What SHAP means
SHAP (SHapley Additive exPlanations) splits a single prediction into contributions from each feature. A positive SHAP value means the feature pushed this order's delay risk up; a negative value pushed it down. The chatbot lists the top positive drivers as risk drivers and the top negative ones as protective factors.

## How this chatbot works (Retrieval-Augmented Generation)
The chatbot uses Retrieval-Augmented Generation (RAG). When a user asks a question, a retriever searches a knowledge base made of this overview, the operations playbook, the data dictionary, an analytics summary, and one record per scored order. The most relevant passages, plus any order the user names by ID, are added to the prompt, and a Claude language model writes an answer grounded only in those passages, citing its sources. Retrieval uses TF-IDF keyword and phrase similarity, which runs quickly on a free CPU and needs no extra model download.

## Data sources
- ERP: customers, materials, sales order headers with release time and required ship-by time.
- WMS: order lines, pick tasks, hourly zone backlog snapshots, weekly inventory snapshots.
- Labor: employees and daily clock-in and clock-out events.
- Carrier: carrier master with daily cutoff times, and shipment confirmations.
All data is synthetic, generated for a graduate course project, and does not describe a real company.
