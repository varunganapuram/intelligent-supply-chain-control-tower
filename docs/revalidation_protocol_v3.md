# Probability-focused revalidation (v3)

The original March-only calibration failed. Version 2's later sigmoid calibration also failed its fixed gates; its artifacts are retained in `reports/legacy_v2/`. Version 3 changes the selection objective to probability quality and compares calibration methods on a forward validation cohort instead of automatically applying a sigmoid transformation.

This protocol is specified before the v3 fitting run. It does not claim that the historical evaluation data is newly unseen; all July–August Olist outcomes were examined in earlier versions. All acceptance gates remain unchanged from v2, and every attempted version is retained.

| Stage | Purchase cohort | Label cutoff |
|---|---|---|
| Base-model training | Before January 2018 | Before 1 February 2018 |
| Calibration-method fitting for selection | February 2018 | Before 1 April 2018 |
| Forward model/method selection | April 2018 | Before 1 June 2018 |
| Final calibration fit and threshold definition | May 2018 | Before 1 July 2018 |
| Retrospective evaluation | July–August 2018 | Final historical extract |

The training parameters are available before the method-fitting cohort. Method-fitting outcomes are known before the forward-validation cohort. Final fitting and selection are available before the July evaluation purchases. January, March and June purchase gaps allow outcomes to mature. Missing delivered-only labels remain excluded and are reported.

Compare the existing fixed constant, logistic and two gradient-boosting base estimators. For each nonconstant estimator, compare raw probabilities, sigmoid calibration and monotone isotonic calibration. Fit the latter two only on February method-fitting rows, then evaluate all pairs on April. Select the lowest validation Brier among pairs whose validation average precision exceeds validation late prevalence by at least 5% relative; break ties by higher average precision. If none qualify, retain the constant baseline and report the failure to establish ranking usefulness. The final calibration method is refitted on May, without changing the selected base model or method using July–August outcomes.

Acceptance gates remain: finite [0,1] probabilities; absolute pooled bias <=2 percentage points; 10 equal-frequency-bin ECE <=2 percentage points; Brier no worse than the constant estimated from the final calibration cohort; each evaluation month absolute bias <=3 percentage points. Publish all gate results and day-clustered bootstrap intervals. Do not relax gates after evaluation.

Raw probabilities are a valid calibration candidate: a transformation is retained only if forward validation supports it. A passing retrospective result establishes only historical statistical acceptance. It does not establish performance on present-day live orders, causal intervention benefit, or production authorization.
