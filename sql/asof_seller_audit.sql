-- Independent SQL equivalent of the primary-seller history lookup.
-- Restrict target to one seller so it matches the Python single-seller semantics.
with target as (
 select * from marts.fct_order where seller_count=1
 order by order_purchase_timestamp desc limit 100
)
select target.order_id, target.order_purchase_timestamp as prediction_as_of,
 h.prior_orders, (h.prior_late+1.4)/(h.prior_orders+20) as seller_prior_late_rate,
 h.latest_known_outcome
from target
left join lateral (
 select count(*) as prior_orders, coalesce(sum(past.is_late),0) as prior_late,
 max(past.order_delivered_customer_date) as latest_known_outcome
 from marts.fct_order past
 where past.primary_seller_id=target.primary_seller_id and past.seller_count=1
 and past.is_late is not null
 and past.order_delivered_customer_date<target.order_purchase_timestamp
) h on true
order by target.order_purchase_timestamp desc;
