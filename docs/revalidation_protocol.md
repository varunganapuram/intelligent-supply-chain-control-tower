# Calibration revalidation protocol (v2)

This protocol is fixed before fitting and evaluating the revised model. Its purpose is to replace the failed March-only probability calibration with a later, mature calibration cohort, then assess the revised probabilities on later purchases.

## Windows and information cutoffs

| Use | Purchase window | Outcomes must be known before |
|---|---|---|
| Training | Before 1 February 2018 | 1 March 2018 |
| Candidate selection | March 2018 | 1 May 2018 |
| Probability calibration and risk thresholds | April–May 2018 | 1 July 2018 |
| Retrospective evaluation | July–August 2018 | Final historical extract |

The revised model is available from 1 July 2018. February purchases leave a maturation gap before March candidate validation, so training outcomes do not postdate validation purchase cutoffs. June purchases are a maturation gap rather than calibration observations. Training preprocessing uses training rows only; model selection uses validation average precision; a sigmoid calibrator is fitted only on the separate calibration cohort. Delivered-only labels and source attribute availability assumptions remain unchanged.

## Acceptance gates, specified before evaluation

- All probabilities finite and within [0, 1].
- Absolute pooled predicted-minus-observed late-rate error at most 2 percentage points.
- Equal-frequency 10-bin expected calibration error at most 2 percentage points.
- Brier score no worse than the constant probability estimated from the calibration cohort, not the evaluation outcomes.
- Each evaluation purchase month: absolute mean probability error at most 3 percentage points.

Report all gates, calibration curves, day-clustered bootstrap intervals, monthly/segment coverage and model comparisons. Do not change thresholds or choose another model using evaluation results. A failed gate remains a failed gate.

## Interpretation

All Olist periods were examined in the earlier project. July–August are held out from the revised fitting procedure but are not a newly collected or previously unseen external test. This is a transparent retrospective revalidation, not a prospective production trial. Historical statistical acceptance does not establish calibration on current live orders or intervention effectiveness. Operational rollout requires representative future data, monitoring and a controlled pilot.

The previous model and evaluation are retained as legacy evidence so the original calibration failure is not hidden.
