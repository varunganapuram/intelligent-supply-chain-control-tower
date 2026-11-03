import numpy as np
import pandas as pd
import pytest
from src.optimization import Scenario,optimize
from src.features import prior_seller_history,FEATURES
from src.models import score

def candidates():
    return pd.DataFrame({'order_id':['a','b','c','d'],'risk_probability':[.9,.8,.7,.1],
        'item_value':[100.,500.,100.,50.],'customer_state':['SP','SP','RJ','RJ']})

def test_constraints_and_exact_small_optimum():
    s=Scenario(capacity=2,budget=10,cost=5,effectiveness=.5,impact=100,value_fraction=0,region_cap=1)
    r=optimize(candidates(),s)
    assert set(r.loc[r.selected_for_intervention,'order_id'])=={'a','c'}
    assert r.loc[r.selected_for_intervention,'intervention_cost'].sum()<=10

@pytest.mark.parametrize('s',[Scenario(capacity=0),Scenario(budget=0),Scenario(effectiveness=0),Scenario(region_cap=0)])
def test_empty_queue_is_valid(s):
    assert not optimize(candidates(),s).selected_for_intervention.any()

def test_empty_candidates():
    assert optimize(candidates().iloc[:0]).empty

def test_reject_invalid_inputs():
    with pytest.raises(ValueError):optimize(candidates(),Scenario(effectiveness=1.5))
    with pytest.raises(ValueError):optimize(pd.concat([candidates(),candidates()]))
    c=candidates();c.loc[0,'risk_probability']=np.nan
    with pytest.raises(ValueError):optimize(c)

def test_future_outcomes_cannot_change_purchase_features():
    o=pd.DataFrame({'order_id':['past','target','future'],
        'order_purchase_timestamp':pd.to_datetime(['2018-01-01','2018-02-01','2018-02-02']),
        'order_delivered_customer_date':pd.to_datetime(['2018-01-10','2018-02-10','2018-02-20']),
        'seller_count':[1,1,1],'is_late':[0.,1.,1.]})
    bridge=pd.DataFrame({'order_id':o.order_id,'seller_id':['s']*3})
    before=prior_seller_history(o,bridge).set_index('order_id').loc['target']
    o.loc[o.order_id.isin(['target','future']),'is_late']=0
    after=prior_seller_history(o,bridge).set_index('order_id').loc['target']
    pd.testing.assert_series_equal(before,after)
    assert before.seller_prior_orders==1
    assert before.history_latest_outcome_at<pd.Timestamp('2018-02-01')

def test_equal_time_outcome_is_excluded():
    o=pd.DataFrame({'order_id':['past','target'],'order_purchase_timestamp':pd.to_datetime(['2018-01-01','2018-02-01']),
        'order_delivered_customer_date':pd.to_datetime(['2018-02-01','2018-02-10']),'seller_count':[1,1],'is_late':[1.,0.]})
    b=pd.DataFrame({'order_id':o.order_id,'seller_id':['s']*2})
    assert prior_seller_history(o,b).set_index('order_id').loc['target','seller_prior_orders']==0

def test_predictor_allowlist_and_schema_guard():
    for forbidden in ['is_late','review_score','order_status','delivery_days','order_delivered_customer_date','label_known_at']:
        assert forbidden not in FEATURES
    with pytest.raises(ValueError,match='schema mismatch'):
        score({'features':FEATURES},pd.DataFrame({'order_id':['x']}))
