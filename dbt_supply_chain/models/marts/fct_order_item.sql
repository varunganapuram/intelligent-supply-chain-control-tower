{{ config(indexes=[{'columns':['order_id']}, {'columns':['seller_id']}]) }}
select i.*, p.category, p.product_weight_g,
 p.product_length_cm*p.product_height_cm*p.product_width_cm as volume_cm3,
 s.seller_state
from {{ ref('stg_order_items') }} i
left join {{ ref('dim_product') }} p using (product_id)
left join {{ ref('dim_seller') }} s using (seller_id)
