with monthly as (
 select date_trunc('month',order_purchase_timestamp)::date as purchase_month,
 count(*) as total_orders,count(is_late) as eligible_orders,sum(is_late) as late_orders,
 avg(is_late) as late_rate,avg(delivery_days) as avg_delivery_days,
 percentile_cont(0.9) within group(order by delivery_days) as p90_delivery_days,
 sum(item_value) as item_value
 from {{ ref('fct_order') }} group by 1
)
select *, lag(late_rate) over(order by purchase_month) as prior_month_late_rate,
 lead(late_rate) over(order by purchase_month) as next_month_late_rate,
 sum(late_orders) over(order by purchase_month rows between 2 preceding and current row)::float /
 nullif(sum(eligible_orders) over(order by purchase_month rows between 2 preceding and current row),0) as rolling_3m_late_rate
from monthly
