select primary_category, count(is_late) as eligible_orders,sum(is_late) as late_orders,
 avg(is_late) as late_rate,avg(delivery_days) as avg_delivery_days
from {{ ref('fct_order') }} group by 1
