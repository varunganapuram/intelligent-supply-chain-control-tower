import json
import numpy as np
import pandas as pd
import pytest
from src.common import ROOT

@pytest.fixture
def built():
    if not (ROOT/'reports/model_evaluation.json').exists():
        pytest.skip('Run pipeline to enable integration artifact checks')
    return ROOT

def test_scoring_time_and_grain(built):
    f=pd.read_parquet(ROOT/'data/processed/ml_delivery_features.parquet')
    r=pd.read_parquet(ROOT/'data/processed/fct_order_risk.parquet')
    assert not f.order_id.duplicated().any()
    assert not r.duplicated(['order_id','scoring_run_id']).any()
    assert r.risk_probability.between(0,1).all()
    assert (r.model_available_at<=r.prediction_as_of).all()
    history=f.dropna(subset=['history_latest_outcome_at'])
    assert (history.history_latest_outcome_at<history.prediction_as_of).all()

def test_mature_training_labels(built):
    m=json.loads((ROOT/'reports/model_evaluation.json').read_text())
    for name,cutoff in m['label_cutoffs'].items():
        assert pd.Timestamp(m['splits'][name]['max_label_known_at'])<pd.Timestamp(cutoff)
    assert pd.Timestamp(m['splits']['train']['max_label_known_at'])<pd.Timestamp(m['splits']['validation']['purchase_min'])
    assert pd.Timestamp(m['splits']['train']['max_label_known_at'])<pd.Timestamp(m['splits']['method_fit']['purchase_min'])
    assert pd.Timestamp(m['splits']['method_fit']['max_label_known_at'])<pd.Timestamp(m['splits']['validation']['purchase_min'])
    assert pd.Timestamp(m['splits']['calibration']['max_label_known_at'])<pd.Timestamp(m['model_available_at'])

def test_generated_scenarios_respect_daily_limits(built):
    f=pd.read_parquet(ROOT/'data/processed/fct_intervention_scenario.parquet')
    scenarios=pd.read_parquet(ROOT/'data/processed/dim_scenario.parquet')
    chosen=f[f.selected_for_intervention]
    for _,s in scenarios.iterrows():
        subset=chosen[chosen.scenario_id.eq(s.scenario_id)]
        assert subset.groupby('replay_day').size().max()<=s.capacity
        assert subset.groupby('replay_day').intervention_cost.sum().max()<=s.budget+1e-8
    assert not f.duplicated(['order_id','scenario_id']).any()

def test_source_and_warehouse_revenue(built):
    o=pd.read_parquet(ROOT/'data/processed/fct_order.parquet')
    i=pd.read_parquet(ROOT/'data/processed/fct_order_item.parquet')
    assert not o.order_id.duplicated().any()
    assert np.isclose(pd.to_numeric(o.item_value).sum(),pd.to_numeric(i.price).sum())
    k=json.loads((ROOT/'reports/kpis.json').read_text())
    assert o.is_late.notna().sum()==k['eligible_orders']
    assert int(o.is_late.sum())==k['late_orders']

def test_sql_python_asof_reconciliation(built):
    p=ROOT/'reports/asof_sql_python_reconciliation.csv'
    if not p.exists():
        pytest.skip('Run scripts/verify_handoff.py for independent SQL reconciliation')
    a=pd.read_csv(p)
    assert len(a)==100 and a.count_matches.all() and a.rate_matches.all()

def test_powerbi_project_required_files(built):
    folder=ROOT/'powerbi/ControlTower.Report'
    for path in ['definition.pbir','definition/report.json','definition/version.json','definition/pages/pages.json']:
        assert (folder/path).is_file(),f'Missing required Power BI project file: {path}'
    assert (ROOT/'powerbi/ControlTower.SemanticModel/model.bim').is_file()
