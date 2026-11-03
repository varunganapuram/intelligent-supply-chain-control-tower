select 'order_count' as failed_check where
 (select count(*) from {{ ref('fct_order') }})<>(select count(*) from {{ ref('stg_orders') }})
union all select 'item_revenue' where
 (select sum(item_value) from {{ ref('fct_order') }})<>(select sum(price) from {{ ref('stg_order_items') }})
union all select 'payment_value' where
 (select sum(payment_value) from {{ ref('fct_order') }})<>(select sum(payment_value) from {{ ref('stg_order_payments') }})
union all select 'item_composite_key' where exists (
 select order_id,order_item_id from {{ ref('fct_order_item') }} group by 1,2 having count(*)>1)
union all select 'seller_bridge_key' where exists (
 select order_id,seller_id from {{ ref('fct_order_seller') }} group by 1,2 having count(*)>1)
