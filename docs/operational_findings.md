# Operational findings

## Observed performance

99,441 orders, 96,470 eligible deliveries, 6,534 late deliveries: on-time rate **93.23%**. P90 delivery is 23.1 elapsed days. 2,971 orders are outside the delivered-order punctuality denominator.

## Geographic investigation queue

| customer_state   |   eligible_orders |   late_rate |   late_rate_ci_low |   late_rate_ci_high |   p90_delivery_days |
|:-----------------|------------------:|------------:|-------------------:|--------------------:|--------------------:|
| MA               |               717 |    0.174338 |          0.148322  |            0.203824 |             34.3159 |
| CE               |              1279 |    0.137608 |          0.11981   |            0.157575 |             34.719  |
| BA               |              3256 |    0.121622 |          0.110838  |            0.133297 |             31.8125 |
| RJ               |             12350 |    0.121053 |          0.115417  |            0.126924 |             29.087  |
| PA               |               946 |    0.112051 |          0.0934985 |            0.133741 |             39.2348 |

Prioritize investigation of high-rate, high-volume regions and inspect within-category comparisons in region_category_strata.csv. Regional differences may reflect promises, route mix, sellers, seasonality or source quality; they are not causal effects. Wilson intervals describe binomial rate uncertainty, not correction for multiple comparisons or seller/time clustering.

## Fulfillment and customer experience

|   handoff_after_item_deadline |   orders |   late_rate |   avg_handoff_days |   avg_transit_days |
|------------------------------:|---------:|------------:|-------------------:|-------------------:|
|                             0 |    79128 |   0.0556567 |            2.56762 |            9.38955 |
|                             1 |     7706 |   0.210096  |            9.66908 |            9.9675  |

Stage analysis is limited to one item and one seller with available handoff/deadline timestamps. Handoff associations warrant checking seller dispatch and carrier event recording. Long transit and late handoff can overlap; do not add them as independent causes. Customer-review comparisons are in customer_experience.csv and require reviewed orders; the dataset cannot represent unreviewed experiences.

## Ranking and decisions

Highest-risk ranking captured 163 eventual late deliveries among 2,890 selected with eligible labels. The optimized 20% assumed-effectiveness scenario selected 1,647 cases and captured 130 eventual late deliveries. Queue sizes differ because allocation may leave capacity unused when expected net benefit is nonpositive.

The selected probability method overestimates later-period risk: mean predicted 8.00% versus observed 4.81%. Its test Brier 0.0480 is worse than the constant baseline 0.0458. Ranking still exceeds prevalence on average precision, but these probabilities do not pass an operational calibration acceptance gate. Monetary outputs remain demonstrative scenarios; retrain and revalidate prospectively before real decisions.

Compare observed late-case capture separately from expected net benefit. Assumptions are BRL 5/case, BRL 150 base delay impact + 25% of item value, BRL 500 daily budget, 50 cases/day, maximum 50/state and 20% assumed effectiveness. The 10%/30% alternatives are sensitivity scenarios, not measured effects. No avoided delays or actual savings are established.

## Management actions

1. Audit high-volume regional and seller groups using sample sizes, uncertainty and primary-category strata.
2. Validate timestamp anomalies and whether checkout promises/seller assignments are version-stable.
3. Review the model reliability curve and segment performance before using risk probabilities for monetary decisions.
4. Pilot interventions prospectively; measure incremental outcome improvements and actual costs before adopting a value objective.
