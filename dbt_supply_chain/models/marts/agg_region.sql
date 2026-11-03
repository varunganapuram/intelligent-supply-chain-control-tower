select customer_state, count(*) as orders,count(is_late) as eligible_orders,
 sum(is_late) as late_orders,avg(is_late) as late_rate,
 avg(delivery_days) as avg_delivery_days,
 percentile_cont(0.9) within group(order by delivery_days) as p90_delivery_days,
 avg(distance_km) as avg_distance_km
from {{ ref('fct_order') }} group by 1
