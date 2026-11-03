# Model card

Model version: **purchase-v3-frozen-20180701**. Selected candidate: **logistic__raw**, selected by forward validation Brier score among candidates with useful validation ranking. Available for replay on **1 July 2018**. Checkout-time lateness prediction conditional on eventual eligible delivery, not all-cause order failure.

## Development windows and label availability

Training purchases precede January 2018, with labels known before February. February outcomes known before April fit raw/sigmoid/isotonic method candidates. April validation, known before June, selects the base/method pair by Brier score with a ranking guard. May data, known before July, defines the final calibration and risk thresholds. July-August purchases form the retrospective evaluation. The exact protocol is in revalidation_protocol_v3.md; legacy failures are retained. Source delivery timestamps approximate when eligible labels became observable; no status-event audit trail is available.

|             |     n | purchase_min        | purchase_max        | max_label_known_at   |
|:------------|------:|:--------------------|:--------------------|:---------------------|
| train       | 43609 | 2016-09-15 12:16:38 | 2017-12-31 23:29:31 | 2018-01-31 23:45:08  |
| method_fit  |  6231 | 2018-02-01 00:24:55 | 2018-02-28 23:57:55 | 2018-03-31 13:51:44  |
| validation  |  6715 | 2018-04-01 00:11:32 | 2018-04-30 23:47:26 | 2018-05-31 00:09:39  |
| calibration |  6726 | 2018-05-01 00:02:11 | 2018-05-31 23:51:24 | 2018-06-30 17:35:34  |
| test        | 12507 | 2018-07-01 00:25:07 | 2018-08-29 15:00:37 | 2018-10-02 00:18:50  |

The buffers reduce preferential inclusion of quick deliveries but cannot eliminate right censoring or delivered-only selection. Label coverage by period must be considered when interpreting results. The final data extraction supplies outcomes through October 2018.

## Measured out-of-time performance

- ROC-AUC: 0.6338
- Average precision: 0.0724; day-bootstrap 95% interval 0.0598-0.0855
- Test late prevalence: 4.81%
- Brier score: 0.0480
- Precision at 50 per purchase day: 5.69%; recall 27.95%

**Probability acceptance finding:** The selected probability method overestimates later-period risk: mean predicted 8.00% versus observed 4.81%. Its test Brier 0.0480 is worse than the constant baseline 0.0458. Ranking still exceeds prevalence on average precision, but these probabilities do not pass an operational calibration acceptance gate. Monetary outputs remain demonstrative scenarios; retrain and revalidate prospectively before real decisions.

`reports/model_comparison.csv` includes constant, logistic and two fixed gradient-boosting candidates. Preprocessing is fitted on training rows only. Raw probabilities, sigmoid and isotonic methods were compared on forward validation. The selected method is refitted on the final calibration cohort; raw selection retains the estimator probabilities. Calibration is not guaranteed under temporal distribution shift; the reliability curve and Brier score must be read with prevalence. All Olist evaluation periods were previously examined during development. This is retrospective revalidation, not a newly unseen or prospective test. Versioned attempts and the unchanged acceptance gates are published.

Risk thresholds: High >= 0.099014; Medium >= 0.057778. These are calibration 90th/70th percentiles, not guaranteed daily workload caps; the optimizer controls actual capacity. Calibration high-risk workload is 673 of 6726 eligible cases.

## Explanations and limitations

The allowlist is documented in `feature_dictionary.md`. Seller outcomes must strictly precede each purchase; equal-time outcomes are excluded. Final status, actual shipping/delivery events, durations, payments and reviews never enter predictors. Historical product metadata, price and seller assignment are assumed to reflect checkout attributes; Olist cannot verify this immutability.

Global importance uses validation-frozen model permutation importance on a fixed test sample; it explains ranking associations. Local examples replace one feature with its calibration-cohort reference value. These are nonadditive reference comparisons, not SHAP values and not causal intervention effects. Adjusted logistic coefficients provide conditional associations, with numeric features standardized and categorical encodings correlated.

Model performance varies by region, category, missing-distance and seller history; see model_segments.csv. Feature missingness and means by split are exported for drift review. Sparse segment estimates are unstable. Retraining, probability monitoring and an intervention pilot are prerequisites for real use. The package versions are locked; only load trusted joblib files.

## Rejected follow-up experiment

The v4 rolling-origin attempt was run once under `docs/revalidation_protocol_v4.md`. It failed the same statistical gates and was not promoted. Its source, cutoff summaries, metrics and outcome are retained in `src/experiments/` and `reports/legacy_v4/`. Run `python scripts/revalidate_v4.py` to reproduce it without changing this published v3 model or database. No new independent test can be claimed on the repeatedly examined Olist evaluation outcomes.
