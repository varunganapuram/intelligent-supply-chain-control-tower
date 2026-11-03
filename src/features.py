"""Purchase-time features. Historical seller labels become observable at delivery."""
import numpy as np
import pandas as pd
from src.common import query, publish_frame

NUMERIC = ['item_value','freight_value','weight_g','volume_cm3','distance_km',
           'item_count','seller_count','promised_days','purchase_month','purchase_weekday',
           'seller_prior_late_rate','seller_prior_orders']
CATEGORICAL = ['customer_state','primary_seller_state','primary_category']
FEATURES = NUMERIC + CATEGORICAL

def prior_seller_history(orders, bridge):
    """Strict event-time search; no outcome from the order being predicted can enter."""
    labeled = orders.loc[orders.is_late.notna(), ['order_id','order_delivered_customer_date','is_late']]
    events = bridge[['order_id','seller_id']].merge(labeled, on='order_id', validate='many_to_one')
    # Multi-seller outcomes are excluded from seller reliability to avoid assigning blame.
    single = set(orders.loc[orders.seller_count.eq(1), 'order_id'])
    events = events[events.order_id.isin(single)].sort_values('order_delivered_customer_date')
    queries = bridge[['order_id','seller_id']].merge(orders[['order_id','order_purchase_timestamp']], on='order_id', validate='many_to_one')
    results = []
    lookup = {s:g for s,g in events.groupby('seller_id',sort=False)}
    for seller, g in queries.groupby('seller_id',sort=False):
        ev = lookup.get(seller)
        n = np.zeros(len(g), dtype=int)
        late = np.zeros(len(g))
        last = np.full(len(g), np.datetime64('NaT','ns'), dtype='datetime64[ns]')
        if ev is not None:
            times = ev.order_delivered_customer_date.to_numpy(dtype='datetime64[ns]')
            n = np.searchsorted(times, g.order_purchase_timestamp.to_numpy(dtype='datetime64[ns]'), side='left')
            sums = np.r_[0., ev.is_late.to_numpy(dtype=float).cumsum()]
            late = sums[n]
            nonzero = n>0
            last[nonzero] = times[n[nonzero]-1]
        results.append(pd.DataFrame({'order_id':g.order_id.to_numpy(),
            'seller_prior_late_rate':(late+1.4)/(n+20), # fixed prior 7%, 20 pseudo-observations
            'seller_prior_orders':n,'history_latest_outcome_at':last}))
    result = pd.concat(results,ignore_index=True).groupby('order_id').agg(
        seller_prior_late_rate=('seller_prior_late_rate','mean'),
        seller_prior_orders=('seller_prior_orders','sum'),
        history_latest_outcome_at=('history_latest_outcome_at','max')).reset_index()
    return result

def run():
    orders = query('select * from marts.fct_order')
    for c in ['order_purchase_timestamp','order_delivered_customer_date','order_estimated_delivery_date']:
        orders[c] = pd.to_datetime(orders[c])
    for c in NUMERIC:
        if c in orders:
            orders[c] = pd.to_numeric(orders[c], errors='coerce')
    orders['is_late'] = pd.to_numeric(orders.is_late,errors='coerce')
    bridge = query('select order_id,seller_id from marts.fct_order_seller')
    history = prior_seller_history(orders,bridge)
    f = orders.merge(history,on='order_id',how='left',validate='one_to_one')
    f['seller_prior_orders'] = f.seller_prior_orders.fillna(0)
    f['seller_prior_late_rate'] = f.seller_prior_late_rate.fillna(.07)
    f['purchase_month'] = f.order_purchase_timestamp.dt.month
    f['purchase_weekday'] = f.order_purchase_timestamp.dt.weekday
    f['prediction_as_of'] = f.order_purchase_timestamp
    f['label_known_at'] = f.order_delivered_customer_date.where(f.is_late.notna())
    for c in CATEGORICAL:
        f[c] = f[c].fillna('unknown').astype(str)
    keep = ['order_id','prediction_as_of','label_known_at','history_latest_outcome_at','is_late']+FEATURES
    f = f[keep].sort_values(['prediction_as_of','order_id']).reset_index(drop=True)
    assert not ((f.history_latest_outcome_at>=f.prediction_as_of)&f.history_latest_outcome_at.notna()).any()
    publish_frame('ml_delivery_features',f)
    return f
