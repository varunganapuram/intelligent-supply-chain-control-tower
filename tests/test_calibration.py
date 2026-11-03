import numpy as np
import pandas as pd
from src.models import ProbabilityCalibrator,logit
from src.common import ROOT
import json

def test_raw_probability_round_trip():
    p=np.array([.001,.05,.25,.8,.999])
    model=ProbabilityCalibrator('raw').fit(logit(p),[0,0,0,1,1])
    assert np.allclose(model.predict_proba(logit(p))[:,1],p)

def test_sigmoid_and_isotonic_handle_extreme_future_scores():
    x=logit(np.linspace(.01,.99,100))
    y=np.r_[np.zeros(70),np.ones(30)]
    for method in ['sigmoid','isotonic']:
        model=ProbabilityCalibrator(method).fit(x,y)
        result=model.predict_proba(np.array([[-100.],[0.],[100.]]))
        assert np.isfinite(result).all()
        assert ((result>=0)&(result<=1)).all()
        assert np.allclose(result.sum(axis=1),1)
        assert np.all(np.diff(result[:,1])>=0)

def test_revalidation_gate_status_cannot_hide_failures():
    path=ROOT/'reports/calibration_revalidation.json'
    if not path.exists():
        return
    report=json.loads(path.read_text())
    assert report['retrospective_accepted']==all(report['acceptance_gates'].values())
    assert report['independent_prospective_test'] is False
    assert report['operational_use_approved'] is False
