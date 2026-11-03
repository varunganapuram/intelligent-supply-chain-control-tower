"""Cross-engine as-of reconciliation and handoff evidence inventory."""
from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.common import ROOT,query,write_json

def main():
    sql=(ROOT/'sql/asof_seller_audit.sql').read_text()
    audit=query(sql)
    features=pd.read_parquet(ROOT/'data/processed/ml_delivery_features.parquet')
    joined=audit.merge(features[['order_id','seller_prior_late_rate','seller_prior_orders','history_latest_outcome_at']],on='order_id',validate='one_to_one',suffixes=('_sql','_python'))
    joined['count_matches']=joined.prior_orders.eq(joined.seller_prior_orders)
    joined['rate_matches']=np.isclose(pd.to_numeric(joined.seller_prior_late_rate_sql),joined.seller_prior_late_rate_python,atol=1e-12)
    assert len(joined)==100 and joined.count_matches.all() and joined.rate_matches.all()
    joined.to_csv(ROOT/'reports/asof_sql_python_reconciliation.csv',index=False)
    artifacts=['reports/kpis.json','reports/model_evaluation.json','reports/dbt_run_results.json','reports/browser_checks.json',
        'reports/powerbi_validation.json','reports/pipeline_run.json','artifacts/delivery_model.joblib','data/processed/fct_order.parquet']
    write_json('reports/handoff_validation.json',dict(asof_sql_python_orders_verified=len(joined),
        artifacts_present={a:(ROOT/a).exists() for a in artifacts}))
    print('SQL vs Python seller history: 100/100 match')

if __name__=='__main__':main()
