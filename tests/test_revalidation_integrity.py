"""Independent checks of persisted probability evidence and delayed-label boundaries."""
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss
from src.common import ROOT
from src.models import score
from src.experiments.rolling_v4 import cohort

def test_reported_quality_matches_persisted_model_predictions():
    f=pd.read_parquet(ROOT/'data/processed/ml_delivery_features.parquet')
    f=f[(f.prediction_as_of>='2018-07-01')&(f.prediction_as_of<'2018-09-01')&f.is_late.notna()]
    bundle=joblib.load(ROOT/'artifacts/delivery_model.joblib')
    r=json.loads((ROOT/'reports/calibration_revalidation.json').read_text())
    p=score(bundle,f)
    assert bundle['model_version']==r['model_version']
    assert np.isclose(p.mean(),r['mean_predicted_risk'],atol=1e-12)
    assert np.isclose(f.is_late.mean(),r['observed_late_rate'],atol=1e-12)
    assert np.isclose(brier_score_loss(f.is_late,p),r['calibrated_brier'],atol=1e-12)
    assert bundle['operational_use_approved'] is False

def test_forward_cohort_excludes_boundary_and_unobserved_labels():
    f=pd.DataFrame({'order_id':['eligible','late_label','at_end','at_cutoff','missing'],
        'prediction_as_of':pd.to_datetime(['2018-01-02','2018-01-03','2018-02-01','2018-01-04','2018-01-05']),
        'label_known_at':pd.to_datetime(['2018-02-10','2018-03-05','2018-02-15','2018-03-01',None]),
        'is_late':[0,1,0,1,np.nan]})
    selected=cohort(f,pd.Timestamp('2018-01-01'),pd.Timestamp('2018-02-01'),pd.Timestamp('2018-03-01'))
    assert selected.order_id.tolist()==['eligible']
