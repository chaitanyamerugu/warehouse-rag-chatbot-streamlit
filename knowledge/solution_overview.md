# Warehouse Management AI Chatbot: Solution Overview

## Business problem
Warehouses need to know which customer orders are likely to miss their shipping deadline while there is still time to act. Distribution centers and e-commerce businesses process orders under fluctuating demand, limited labor, uneven inventory availability, and fixed carrier cutoffs. Late orders drive overtime, expedited freight, SLA chargebacks, lower customer satisfaction, and end-of-day pressure on frontline workers. Most warehouse management systems rely on predefined rules and end-of-shift reports, so supervisors often learn an order is late only after the cutoff has passed.

## Prediction task
For each new order, a delay prediction model (XGBoost) estimates the probability that it will ship after its required carrier cutoff, using only information available when the order is released. Orders above the alert threshold are flagged at risk. SHAP values show the top factors behind each score, such as items only in reserve locations or high backlog in its zone (Lundberg and Lee, 2017).

## What the chatbot adds
Supervisors should not need to read tables to act. The Generative AI chatbot answers plain-English questions about at-risk orders, inventory, shipping delays, and labor attendance, explains why an order is at risk, and recommends what to do, citing the data it used.

## How the chatbot works
The chatbot combines Retrieval-Augmented Generation (RAG) with tool use over the warehouse data:
1. Retrieve: for each question, a TF-IDF retriever finds the most relevant passages in the knowledge base (this overview, the operations playbook, the data dictionary, and a precomputed analytics summary). Any record ID in the question (SO-, ORD, PRD, EMP) is looked up directly.
2. Query: when the question needs exact numbers, the model calls safe data tools (query_table, get_record, daily_snapshot) that filter, group, and aggregate the four tables with pandas. No model-written code is executed.
3. Generate: a Claude language model writes a short answer grounded only in the retrieved passages and tool results, and the app shows which documents and queries were used.
The knowledge base and data schema are sent with prompt caching, so repeat questions are fast and inexpensive.

## Data sources
- warehouse_orders: 2,000 orders flagged at risk (July 1 to November 13, 2026) with delay probability, SHAP risk drivers, and suggested actions.
- inventory: 100 products with stock on hand, reorder levels, locations, prices, and status.
- shipping_delays: 200 shipments (September to November 2026) with expected and actual ship dates, delay days, delay reason, and carrier.
- labor_attendance: daily attendance for 60 associates (July 1 to November 14, 2026) with status, clock times, hours, overtime, and absence reasons.
All data is synthetic and created for a graduate course project; it does not describe a real company.

## App tabs
- Chat: ask questions; each answer lists the knowledge passages and data queries it used.
- Dashboard: headline metrics and charts across orders, inventory, shipping, and labor.
- Data explorer: browse, filter, and download each table.
- About: this overview.
