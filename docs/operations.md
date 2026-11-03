# Runbook

## Open the delivered result

The repository contains the full historical dataset and processed local results. It can open the dashboard without PostgreSQL:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-lock.txt
.venv\Scripts\python -m streamlit run app/streamlit_app.py
```

On a fresh clone, raw files and Parquet/model artifacts are ignored. Download/rebuild with the pipeline below. Python 3.12 is the tested interpreter. For another Python version, install the package from `pyproject.toml` and rerun tests rather than assuming binary model compatibility. Only load joblib artifacts from trusted sources.

## Rebuild

1. Copy `.env.example` to `.env`; choose a local password. Do not commit this file.
2. Install Python dependencies with `python -m pip install -e .`.
3. Start PostgreSQL 17 with `docker compose up -d --wait`, or point the PG environment variables at a dedicated local database.
4. Run `python -m src.pipeline`. Missing source files are fetched from the public Kaggle archive; existing originals remain unchanged.
5. Run `python -m pytest -q` and `python scripts/export_powerbi.py`.
6. Run `python scripts/build_portfolio.py` to regenerate notebooks, findings, static report and case study. The data pipeline itself does not depend on PDF generation.

`python -m src.pipeline --from-stage models` resumes from generated features. Other supported start stages: warehouse, analytics, features and optimization. Upstream exports must already exist. The loader replaces only this project's named raw tables; use a dedicated database.

## Local delivered environment

The construction session uses a portable PostgreSQL server under the adjacent workspace `work/` directory, listening only on 127.0.0.1:55432. Its randomly generated password is kept in the ignored local `.env`. The deliverable ZIP excludes that file. Docker is the portable rebuild route on another machine; no database service is installed system-wide.

## Pipeline checks and troubleshooting

- Source schema/key failures stop ingestion; do not silently deduplicate source facts.
- dbt build logs and run-results JSON capture all model and assertion results. Known lifecycle anomalies intentionally warn and are quantified in the quality report.
- Missing outcome labels stay null. Investigate exclusions and incomplete final cohorts before comparing periods.
- Missing model artifact: rerun models. Feature schema mismatch: rebuild features and models together.
- Solver status must be OPTIMAL or FEASIBLE; FEASIBLE is a bounded-time solution, not a proof of optimality.
- Changes to feature definitions, package versions, thresholds or scenario assumptions require regenerating outputs and rerunning tests.
- Reporting snapshots are static; rerun after any source or configuration change. Scheduled runs demonstrate reproducibility of historical data, not new live orders.

## Production next steps

Version source events and promises, record decision timestamps, monitor calibration/coverage by segment, track drift, add consented operational costs, and pilot randomized interventions. Measure intervention uplift and harm before treating simulated value as a forecast. Add secrets management, access control, migrations, lineage storage and multi-table release coordination before enterprise deployment.
