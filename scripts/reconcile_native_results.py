from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
root=Path(__file__).resolve().parents[1]
d=json.loads((root/'reports/native_dax_results.json').read_text(encoding='utf-8-sig'))
k=json.loads((root/'reports/kpis.json').read_text())
checks=[]
def equal(name,a,b,tolerance=1e-8):
    ok=bool(np.isclose(float(a),float(b),atol=tolerance,rtol=1e-9))
    checks.append(dict(check=name,native=float(a),reference=float(b),passed=ok))
    assert ok,(name,a,b)
row=d['totals'][0]
for col,key in [('Total Orders','total_orders'),('Eligible Orders','eligible_orders'),('Late Orders','late_orders'),
    ('On-Time Delivery %','on_time_rate'),('Average Delivery Days','average_delivery_days'),
    ('P90 Delivery Days','p90_delivery_days'),('Item Value','item_value'),('Dissatisfaction %','dissatisfaction_rate')]:
    equal(col,row[f'[{col}]'],k[key],1e-5)
regions=pd.read_csv(root/'reports/agg_region.csv').set_index('customer_state')
for r in d['by_state']:
    state=r['Orders[customer_state]'];ref=regions.loc[state]
    for col,key in [('Orders','orders'),('Eligible','eligible_orders'),('Late','late_orders')]:
        equal(f'{state}:{col}',r[f'[{col}]'] or 0,ref[key] or 0)
    equal(f'{state}:OnTime',r['[OnTime]'],1-ref.late_rate)
monthly=pd.read_csv(root/'reports/agg_monthly.csv');monthly['month']=pd.to_datetime(monthly.purchase_month).dt.strftime('%Y-%m');monthly=monthly.set_index('month')
for r in d['by_month']:
    month=r['Date[year_month]']
    if month not in monthly.index:
        assert r['[Orders]'] is None
        continue
    ref=monthly.loc[month]
    equal(month+':Orders',r['[Orders]'],ref.total_orders)
    equal(month+':Eligible',r['[Eligible]'] or 0,ref.eligible_orders)
    equal(month+':Late',r['[Late]'] or 0,0 if pd.isna(ref.late_orders) else ref.late_orders)
sellers=pd.read_csv(root/'reports/agg_seller.csv').set_index('seller_id')
for r in d['single_seller']:
    seller=r['Sellers[seller_id]']
    if seller not in sellers.index:
        assert r['[Eligible]'] is None
        continue
    ref=sellers.loc[seller]
    equal('seller '+seller+':Eligible',r['[Eligible]'] or 0,ref.eligible_orders)
    if pd.notna(ref.late_rate):equal('seller '+seller+':LateRate',r['[LateRate]'],ref.late_rate)
risks=pd.read_parquet(root/'data/processed/fct_order_risk.parquet');r=d['risk'][0]
equal('Scored rows',r['[Scored]'],len(risks));equal('High risk rows',r['[HighRisk]'],risks.risk_category.eq('High').sum())
m=json.loads((root/'reports/model_evaluation.json').read_text())
equal('Model AP',r['[AP]'],m['test']['average_precision'])
equal('Daily precision',r['[PrecisionAt50]'],m['test']['precision_at_50_daily'])
decisions=pd.read_parquet(root/'data/processed/fct_intervention_scenario.parquet')
selected=decisions[decisions.selected_for_intervention]
for r in d['scenarios']:
    scenario=r['Scenario[scenario_id]'];f=selected[selected.scenario_id.eq(scenario)]
    equal(scenario+':Selected',r['[Selected]'],len(f))
    equal(scenario+':Cost',r['[Cost]'],f.intervention_cost.sum())
    equal(scenario+':Net',r['[NetValue]'],f.expected_net_benefit.sum(),1e-5)
assert d['empty_filter'][0]['[OnTime]'] is None
checks.append(dict(check='Empty-cohort rate stays BLANK',passed=True))
result=dict(status='passed',native_engine='Power BI Desktop 2.159.1231.0',
    refreshed_tables=7,dax_query_groups=len(d),comparisons=len(checks),
    checks=checks,graphics_capture='Unavailable: Windows capture timed out; native accessibility and DAX engine used',
    report_structure_fix='Added required definition/version.json',
    limits='No pixel screenshot validation claimed')
(root/'reports/native_powerbi_acceptance.json').write_text(json.dumps(result,indent=2))
print(f'Native Power BI reconciliation passed: {len(checks)} comparisons')
