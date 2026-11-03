# Interview notes and defensible resume language

**Suggested title:** Intelligent Supply Chain Control Tower: Predictive Delivery Risk, SLA Monitoring & Intervention Optimization.

**Description:** Built an Olist historical operations prototype using PostgreSQL/dbt, Python, chronological delivery-risk modeling, an OR-Tools investigation allocator and a six-page dashboard. Reconciled multi-grain source data, audited purchase-time features and separated observed ranking performance from assumed intervention value.

Use the actual metrics in `reports/model_evaluation.json` when adding measured results. Describe the Power BI artifact as an editable project until it has passed Desktop acceptance. Do not claim deployed real-time tracking, proven savings or a reduction in late deliveries.

1. **Why separate items and payments?** They have independent one-to-many relationships with orders. A direct join multiplies values. Each is aggregated first, then joined once per order.
2. **Why calendar-date SLA?** The promise is represented as a date. Comparing an afternoon delivery with promised midnight would incorrectly label same-day deliveries late.
3. **Why a strict event-time lookup?** An earlier purchase is not enough: its delivery outcome must also have become known before the next order's placement.
4. **Why chronological splits?** They approximate forward deployment and expose temporal shifts; preprocessing, model selection, calibration and thresholds all precede test purchases.
5. **Why AP, Brier and daily precision?** Ranking rare late cases, probability quality and finite review capacity answer different operational questions. Accuracy can reward predicting everything on time.
6. **Why does optimization not always win precision?** Its assumed value objective accounts for financial impact and costs. Highest-risk ranking directly optimizes late-case detection under uniform review effort.
7. **Why not assign failures to every seller?** Delivery timestamps are at order grain; multi-seller attribution is ambiguous. Seller reliability uses single-seller historical orders.
8. **What is still unvalidated?** Attribute immutability at checkout, delivered-only selection bias, censoring near development cutoffs, real intervention efficacy, and production operations.
9. **How would you prove business value?** Run an adequately powered prospective randomized intervention pilot, measuring outcomes and costs against an untreated control with guardrail metrics.
