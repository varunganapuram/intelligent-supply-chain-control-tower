import json
import numpy as np
import pandas as pd
from src.common import ROOT, query, write_json

def wilson(late,n):
    n=np.asarray(n,dtype=float); k=np.asarray(late,dtype=float)
    p=np.divide(k,n,out=np.zeros_like(n),where=n>0); z=1.96
    center=(p+z*z/(2*np.maximum(n,1)))/(1+z*z/np.maximum(n,1))
    half=z*np.sqrt(p*(1-p)/np.maximum(n,1)+z*z/(4*np.maximum(n,1)**2))/(1+z*z/np.maximum(n,1))
    return np.maximum(0,center-half),np.minimum(1,center+half)

def run():
    orders=query('select * from marts.fct_order')
    # PostgreSQL numerics become Decimal; reporting exports use explicit float conversions.
    for c in ['is_late','delivery_days','delay_days','item_value','freight_value','distance_km','handoff_days','transit_days']:
        orders[c]=pd.to_numeric(orders[c],errors='coerce')
    orders.to_parquet(ROOT/'data/processed/fct_order.parquet',index=False)
    orders.to_csv(ROOT/'reports/fct_order.csv',index=False)
    eligible=orders[orders.is_late.notna()]
    reviewed=orders[orders.review_score.notna()]
    kpis=dict(total_orders=len(orders),eligible_orders=len(eligible),excluded_orders=len(orders)-len(eligible),
        late_orders=int(eligible.is_late.sum()),late_rate=float(eligible.is_late.mean()),
        on_time_rate=float(1-eligible.is_late.mean()),average_delivery_days=float(eligible.delivery_days.mean()),
        p90_delivery_days=float(eligible.delivery_days.quantile(.9)),average_delay_days=float(eligible.delay_days.mean()),
        item_value=float(orders.item_value.sum()),freight_value=float(orders.freight_value.sum()),
        payment_value=float(pd.to_numeric(orders.payment_value).sum()),
        reviewed_orders=len(reviewed),dissatisfaction_rate=float(reviewed.review_score.le(2).mean()),
        purchase_min=str(orders.order_purchase_timestamp.min()),purchase_max=str(orders.order_purchase_timestamp.max()))
    # Independent pandas date comparison reconciles SQL KPI.
    independently_late=(pd.to_datetime(eligible.order_delivered_customer_date).dt.normalize()>
                        pd.to_datetime(eligible.order_estimated_delivery_date).dt.normalize()).astype(int)
    assert int(independently_late.sum())==kpis['late_orders']
    write_json('reports/kpis.json',kpis)
    tables=['agg_monthly','agg_region','agg_seller','agg_category','dim_date','dim_customer','dim_seller','dim_product','dim_geography','fct_order_item','fct_order_seller']
    for table in tables:
        frame=query(f'select * from marts.{table}')
        if 'late_orders' in frame and 'eligible_orders' in frame:
            frame['late_rate_ci_low'],frame['late_rate_ci_high']=wilson(frame.late_orders.fillna(0),frame.eligible_orders)
        frame.to_csv(ROOT/'reports'/f'{table}.csv',index=False)
        frame.to_parquet(ROOT/'data/processed'/f'{table}.parquet',index=False)
    status=orders.groupby('order_status').agg(orders=('order_id','size'),eligible=('is_late','count')).reset_index()
    status.to_csv(ROOT/'reports/status_coverage.csv',index=False)
    cq=orders.groupby(['customer_state','primary_category'],dropna=False).agg(eligible=('is_late','count'),late_rate=('is_late','mean')).reset_index()
    cq.to_csv(ROOT/'reports/region_category_strata.csv',index=False)
    cx=orders[orders.is_late.notna()&orders.review_score.notna()].groupby('is_late').agg(reviewed=('review_score','count'),
        dissatisfied=('review_score',lambda x:x.le(2).sum()),average_score=('review_score','mean')).reset_index()
    cx['dissatisfaction_rate']=cx.dissatisfied/cx.reviewed
    cx.to_csv(ROOT/'reports/customer_experience.csv',index=False)
    stages=orders[orders.item_count.eq(1)&orders.seller_count.eq(1)&orders.is_late.notna()&orders.handoff_after_item_deadline.notna()]
    stages.groupby('handoff_after_item_deadline').agg(orders=('order_id','size'),late_rate=('is_late','mean'),
        avg_handoff_days=('handoff_days','mean'),avg_transit_days=('transit_days','mean')).to_csv(ROOT/'reports/fulfillment_stages.csv')
    dq=query("""select count(*) as total_orders,
      count(*) filter(where not eligible_delivery) as ineligible_punctuality,
      count(*) filter(where order_status='delivered' and order_delivered_customer_date is null) as delivered_missing_actual,
      count(*) filter(where order_delivered_carrier_date<order_purchase_timestamp) as carrier_before_purchase,
      count(*) filter(where order_delivered_customer_date<order_delivered_carrier_date) as delivery_before_carrier,
      count(*) filter(where order_approved_at<order_purchase_timestamp) as approval_before_purchase,
      count(*) filter(where seller_count>1) as multi_seller_orders,
      count(*) filter(where item_count>1) as multi_item_orders,
      count(*) filter(where payment_count>1) as multi_payment_orders,
      count(*) filter(where distance_km is null) as distance_missing,
      count(*) filter(where weight_g is null) as weight_missing,
      count(*) filter(where order_estimated_delivery_date is null) as promised_missing
      from marts.fct_order""").iloc[0].to_dict()
    dq['missing_seller_refs']=int(query('select count(*) n from staging.stg_order_items i left join staging.stg_sellers s using(seller_id) where s.seller_id is null').iloc[0,0])
    dq['missing_product_refs']=int(query('select count(*) n from staging.stg_order_items i left join staging.stg_products p using(product_id) where p.product_id is null').iloc[0,0])
    dq['geolocation_outside_brazil_bbox']=int(query('select count(*) from staging.stg_geolocation where geolocation_lat not between -34 and 6 or geolocation_lng not between -74 and -34').iloc[0,0])
    dq['negative_item_amounts']=int(query('select count(*) from staging.stg_order_items where price<0 or freight_value<0').iloc[0,0])
    dq['invalid_product_dimensions']=int(query('select count(*) from staging.stg_products where product_weight_g<=0 or product_length_cm<=0 or product_height_cm<=0 or product_width_cm<=0').iloc[0,0])
    dq['invalid_zip_prefixes']=int(query("select count(*) from staging.stg_customers where customer_zip_code_prefix !~ '^[0-9]{5}$'").iloc[0,0])
    write_json('reports/data_quality.json',{k:int(v) for k,v in dq.items()})
    plans={}
    from src.common import connect
    with connect() as con,con.cursor() as cur:
        cur.execute('analyze marts.fct_order')
        for name,sql in [('monthly','select purchase_date,count(*) from marts.fct_order group by 1'),
                         ('daily_queue',"select order_id from marts.fct_order where purchase_date='2018-06-01'")]:
            cur.execute('explain (analyze,buffers,format json) '+sql)
            plans[name]=cur.fetchone()[0]
    write_json('reports/query_plans.json',plans)
    return kpis
