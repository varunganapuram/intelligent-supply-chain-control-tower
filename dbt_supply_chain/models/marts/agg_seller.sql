select primary_seller_id as seller_id, count(is_late) as eligible_orders,
 sum(is_late) as late_orders, avg(is_late) as late_rate,
 avg(delivery_days) as avg_delivery_days
from {{ ref('fct_order') }} where seller_count=1 group by 1
