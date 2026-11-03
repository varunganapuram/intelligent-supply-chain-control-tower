# Delivery status - 3 November 2026

The runnable historical prototype and local portfolio handoff are delivered. Native Desktop data/measure acceptance and historical calibration revalidation are complete. Calibration acceptance failed, so operational use remains unapproved. Native pixel screenshot review is not claimed.

| Workstream | Delivered / verified evidence |
|---|---|
| Foundation | Business charter, KPI contract, nine unchanged originals, SHA-256 manifest, column/key/null profiling, source schema contract and data quality report |
| Data warehouse | PostgreSQL 17 local execution; 21 dbt staging/mart models; 19 passing assertions and one documented warning for 189 lifecycle anomalies; independent monetary and order-count reconciliation |
| Operational BI | Six working Streamlit pages; browser screenshots and zero-capacity interaction check; 60 Power BI report JSON files pass public schemas; native model parses with Microsoft TOM: 7 tables, 5 relationships, 24 measures |
| Prediction | Strict as-of features; independent SQL/Python history agreement on 100 orders; chronological buffered train/selection/calibration/test; trained artifacts, segment and drift reports, label coverage, explanations and model card |
| Probability acceptance | **Not accepted for operations:** Revalidation completed under v3; mean predicted 8.00%, observed 4.81%; Brier 0.0480 versus calibration-prior baseline 0.0460. Fixed gates failed; operational use not approved |
| Decision optimization | OR-Tools daily allocation; capacity, budget and state caps; same-limit policy comparisons; 10%/20%/30% hypothetical effectiveness scenarios; interactive simulator; no realized impact claimed |
| Integration | Full raw-to-warehouse-to-features-to-model-to-scenarios run succeeded; generated facts published to PostgreSQL and CSV/Parquet; purchase-time scores with day-end batch review; 19 tests pass with zero skips |
| Portfolio | README, 3 executed notebooks (24 code cells), screenshots, 6-page standalone HTML report, 4-page rendered/inspected PDF, approximately five-minute narrated MP4, interview notes, operating guide and public GitHub repository |
| Automation | GitHub Actions workflow with PostgreSQL service, full rebuild, tests, export and monthly schedule; latest execution status is visible at https://github.com/varunganapuram/intelligent-supply-chain-control-tower/actions/workflows/tests.yml |

## Acceptance outcomes and boundaries

1. Native Desktop refresh and DAX acceptance passed. Native Power BI Desktop 2.159.1231.0 opened the project and refreshed all seven tables. Seven DAX query groups passed 6,101 reconciliations against Python/SQL exports, including totals, dates, states, sellers, risks, scenarios and an empty-cohort BLANK check. Desktop accessibility exposed the populated overview cards and all six report tabs. Windows graphics capture timed out, so pixel-level screenshots and a full native visual-interaction review are not claimed. On another computer, set DataFolder and refresh before further visual-interaction review.
2. Public repository: https://github.com/varunganapuram/intelligent-supply-chain-control-tower. Source and workflow are published to main; inspect the workflow page for its latest run. The local handoff also includes the ignored data and trained artifact needed for immediate use.
3. Historical calibration revalidation is complete and failed its fixed acceptance gates. `python scripts/check_model_readiness.py` returns a nonzero status. Do not use these probabilities operationally without representative prospective data, monitoring and a controlled intervention pilot. No causal intervention benefit is established.

The historical replay is a batch of orders purchased on a selected historical date, each scored at placement with a previously available model. It is not a reconstruction of an entire in-flight fleet, live tracking or a production deployment.

## Verification records

- `reports/pipeline_run.json`: successful full rebuild with measured stage times.
- `reports/dbt_run_results.json`: all warehouse model and assertion statuses.
- `reports/pytest_results.xml`: 19 passing Python tests, zero failures/errors/skips.
- `reports/asof_sql_python_reconciliation.csv`: independently checked seller history.
- `reports/browser_checks.json`: six pages and zero-capacity interaction, no errors.
- `reports/powerbi_validation.json`, `reports/powerbi_tom_validation.json`: schema and metadata-parser validation boundaries.
- `reports/final_artifact_checks.json`: offline HTML, executed notebooks and full MP4 decode.
- PDF rendered with Poppler and PyMuPDF and visually inspected across all four pages; no clipped or overlapping content found.

## Presentation revision

The report uses a light layout with plain section names, readable percentages, and state names. Headings use bold black type; subheadings and body text use thin black type. Dashboard charts use saturated RGB colors, solid bars, and thicker lines. The overview pairs delivery rates with order volume and includes calculated notes on the March 2018 spike and the concentration of late orders in SÃƒÂ£o Paulo. Dashboard screenshots, the offline report, Power BI theme and walkthrough follow these typography and chart settings; the PDF remains a separate print report.

All six sections open successfully. Additional browser checks cover the state filter, a regional comparison with no qualifying rows, a daily queue with no selected cases, and the eventual-outcome checkbox. See `reports/revised_filter_checks.json`.

Browser-computed text colors, font weights and chart trace settings are recorded in `reports/typography_color_checks.json`: headings are black at weight 800, subheadings/body are black at weight 300, and the main trend uses a four-pixel RGB blue line.

## Native validation details

Native Power BI Desktop 2.159.1231.0 opened the project and refreshed all seven tables. Seven DAX query groups passed 6,101 reconciliations against Python/SQL exports, including totals, dates, states, sellers, risks, scenarios and an empty-cohort BLANK check. Desktop accessibility exposed the populated overview cards and all six report tabs. Windows graphics capture timed out, so pixel-level screenshots and a full native visual-interaction review are not claimed.

## Calibration revalidation details

The v1, v2 and v3 attempts are retained. V3 compares raw, sigmoid and isotonic methods on a forward validation cohort using probability-focused selection. No failed gate was relaxed or hidden. The evaluated July-August data had been examined in earlier iterations; this is not a newly unseen or prospective test.
