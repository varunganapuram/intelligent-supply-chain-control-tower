# Rolling-origin selection and updated training window (v4)

Specified before the v4 fitting run. V1-v3 and their failed results remain available. All July-August 2018 outcomes have already been examined, so this is explicitly a retrospective development evaluation, not an independent holdout or prospective acceptance. The statistical gates below are unchanged. Do not iterate on July-August results to obtain a pass.

## Correction being evaluated

V3 selected its estimator/method using April alone and kept its base estimator trained only on pre-January purchases. Evaluate stability over four forward folds instead, and refit the selected estimator using the additional mature observations available before final calibration. Training rows and calibration rows stay disjoint. Only labels observed before each fitting cutoff are usable. Never fit on an evaluation order's outcome.

| Forward validation purchases | Base training purchases | Base label cutoff | Calibration purchases | Calibration label cutoff | Validation label cutoff for selection |
|---|---|---|---|---|---|
| February 2018 | Before November 2017 | 1 December 2017 | December 2017 | 1 February 2018 | 1 July 2018 |
| March 2018 | Before December 2017 | 1 January 2018 | January 2018 | 1 March 2018 | 1 July 2018 |
| April 2018 | Before January 2018 | 1 February 2018 | February 2018 | 1 April 2018 | 1 July 2018 |
| May 2018 | Before February 2018 | 1 March 2018 | March 2018 | 1 May 2018 | 1 July 2018 |

Use the same four fixed base estimators and raw/sigmoid/isotonic candidates as v3. Choose the pair with the lowest equally weighted mean validation Brier across the four months, subject to average precision exceeding prevalence by at least 5% relative on the pooled forward predictions. Break ties with higher pooled average precision. If no ranking candidate qualifies, explicitly use the constant baseline and report that useful ranking was not established. No estimator parameters or windows may be selected using July-August outcomes.

For final fitting, train the selected base estimator on purchases before 1 April 2018 with labels known before 1 May. Fit the selected calibration method on May purchases with labels known before 1 July. Freeze both on 1 July for all July-August purchase-time predictions; no July outcomes update August predictions. Thresholds use only May calibration predictions. Final preprocessing is fitted only on final base training rows. Retain fold-level sample IDs/cutoffs and candidate scores for audit.

## Fixed statistical gates

- All probabilities finite and within [0,1].
- Absolute pooled mean bias at most 2 percentage points.
- Ten equal-frequency-bin expected calibration error at most 2 percentage points; a constant prediction produces one bin rather than an empty reliability table.
- Brier no worse than the constant estimated from the final calibration cohort.
- Each evaluation month's absolute mean bias at most 3 percentage points.

Report ranking metrics, monthly quality, label coverage, and day-clustered bootstrap intervals. A historical statistical pass does not authorize operational use. Research submission readiness and operational readiness must be separate, explicit gates. The latter requires representative prospective data and a controlled deployment review that are absent from Olist.

Implementation reference: [scikit-learn probability calibration](https://scikit-learn.org/stable/modules/calibration) requires estimator and calibrator fitting data to be disjoint. The calendar gaps above additionally address delayed delivery labels.
