{{ config(indexes=[{'columns':['order_id']}, {'columns':['seller_id']}]) }}
select order_id, seller_id, count(*) as item_count, sum(price) as item_value,
 sum(freight_value) as freight_value
from {{ ref('stg_order_items') }} group by 1,2
