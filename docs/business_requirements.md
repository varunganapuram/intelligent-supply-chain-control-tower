# Project charter

**Intelligent Supply Chain Control Tower: Predictive Delivery Risk, SLA Monitoring & Intervention Optimization**

Stakeholders: Head of Operations, Supply Chain Manager, Regional Operations Leads.

Decision: identify material delivery reliability problems and choose which purchase-day cases warrant investigation under limited staff and budget.

Primary KPI: calendar-date on-time delivery among valid completed deliveries. Supporting outputs: regional and seller diagnostics, customer experience, calibrated risk estimates and hypothetical intervention scenarios.

The source is Olist's anonymized historical Brazilian marketplace data, 2016-2018. It has no live tracking, actual intervention assignments or observed intervention costs/effects. Use is a noncommercial portfolio prototype under the dataset's CC BY-NC-SA terms.

## Acceptance criteria

- Nine original files remain byte-preserved; checksums and profiles are recorded.
- Order facts have exactly one row per source order. Item and payment sums reconcile independently.
- NULL delivery labels remain unknown; source exclusions and timestamp anomalies are reported.
- Predictions use checkout attributes and previously observed completed-delivery history only.
- Training, model selection, calibration and final evaluation are chronological, with label availability bounded at each development cutoff.
- Optimization respects daily capacity, budget and regional caps, including empty queues and zero-benefit scenarios.
- Every business-value number is labeled as a scenario estimate.
- A working six-page dashboard, model artifacts, reporting exports, tests and operating documentation are delivered.
- Native Power BI requires a Desktop refresh/render acceptance check before claiming the report has been visually validated there.

## Operational scope

Purchase-time scoring estimates lateness conditional on eventually delivered orders. The simulator reviews an end-of-day batch of purchases scored at their individual placement times. It does not reconstruct all in-flight orders. A real deployment would require event-sourced checkout versions, status transitions, operational costs and prospective intervention trials.

## Success measurement

Report observed ranking metrics without promising a minimum improvement. Compare constant prevalence, logistic regression, gradient boosting, shortest promises, prior seller risk, highest-risk ranking and repeated seeded random selection. Optimization has a different objective from pure late-case detection and may not dominate it.
