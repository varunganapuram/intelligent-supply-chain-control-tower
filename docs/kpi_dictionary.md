# KPI dictionary and metric contract

All order KPIs use `marts.fct_order`, one row per order. Amounts are historical Brazilian reais (BRL); item value, freight and payments are distinct quantities and should not be described interchangeably as revenue.

| Metric | Definition / denominator |
|---|---|
| Total orders | Count of all source orders, including canceled and unresolved |
| Eligible delivered | Final status delivered; actual, promised and purchase timestamps present; actual not before purchase; promised calendar date not before purchase calendar date |
| Late orders | Eligible delivered orders whose actual calendar date exceeds promised calendar date |
| Late delivery % | Late / eligible delivered, under the current filter |
| On-time delivery % | 1 - late rate; return blank if the denominator is zero |
| Average delivery days | Mean elapsed seconds from purchase to actual delivery / 86,400 among eligible deliveries |
| P90 delivery days | Linear interpolated 90th percentile of the same eligible elapsed durations |
| Average delay days | Mean max(0, actual calendar date - promised calendar date) among all eligible deliveries |
| Seller late rate | Eligible, **single-seller** orders only; an order-level delivery outcome is an association, not seller responsibility |
| Handoff after item deadline | Carrier handoff timestamp > item shipping deadline, only one-item/one-seller orders with both timestamps |
| Reviewed orders | Orders with a non-null selected review; latest answer, then creation, review ID, score descending break ties |
| Dissatisfaction % | Selected review score 1 or 2 / all reviewed orders (all statuses); late-vs-on-time comparison further requires an eligible outcome |
| High-risk orders | Probability >= 90th percentile of calibrated probabilities in the calibration cohort; Medium >= 70th percentile; remaining Low |
| Precision @ 50/day | Eventual late deliveries / eligible scored deliveries in each purchase day's top min(50, cohort volume), micro-aggregated across days |
| Recall @ 50/day | Late deliveries captured in those daily queues / all eligible late deliveries in the test cohort |
| Average precision | scikit-learn average precision, not trapezoidal PR-AUC |
| Scenario net benefit | Sum(selected probability * assumed effectiveness * assumed impact - assumed case cost) |

The model's reported top-K evaluation is restricted to eligible completed deliveries. Policy evaluation selects from **all** scored purchases, then reports known-outcome precision and unlabeled coverage separately. These denominators differ deliberately.

Historical seller rate: `(prior late single-seller orders + 1.4)/(prior completed single-seller orders + 20)`. The fixed prior is 7% with 20 pseudo-observations; it is not estimated from the test data. Outcomes qualify only when their actual delivery timestamps strictly precede the purchase timestamp. Multiple current sellers use the unweighted mean of seller rates and sum of seller historical counts.

Geographic coordinates: median latitude/longitude per ZIP prefix after a broad Brazil bounding-box filter (-34 to 6 latitude, -74 to -34 longitude). Order distance is mean item seller-to-customer great-circle distance, not route distance. Primary category and primary seller are the first item by `order_item_id`; multi-category order reports describe primary category only.

SQL and pandas reconciliation is executed by the pipeline. Power BI DAX follows this contract, but DAX execution in Desktop must be checked separately using `powerbi/acceptance_queries.dax`.
