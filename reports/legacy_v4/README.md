# V4 outcome: rejected for promotion

This is the single run specified by `docs/revalidation_protocol_v4.md`, retained with its source in `src/experiments/rolling_v4.py`. Run `python scripts/revalidate_v4.py` to reproduce it in an isolated output folder without changing the published estimator or PostgreSQL facts.

The frozen four-fold selection chose `logistic__raw`. Refit on more recent mature training data increased July-August mean predicted risk to 13.63%, versus 4.81% observed. Brier was 0.0610 against the calibration-prior baseline 0.0460. Four statistical acceptance gates failed. This version is not promoted. The existing v3 research model remains the published version and is also explicitly blocked from operational use.

Full row-level fold audits and forward predictions are supplied in the local handoff under `data/processed/revalidation_v4/`; the Git repository retains aggregated scores and cutoff summaries. No acceptance limit was relaxed. No additional parameter search is justified using the repeatedly examined July-August outcomes.
