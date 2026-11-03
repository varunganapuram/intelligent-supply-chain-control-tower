select
  order_id,
  nullif(order_item_id,'')::integer as order_item_id,
  product_id,
  seller_id,
  nullif(shipping_limit_date,'')::timestamp as shipping_limit_date,
  nullif(price,'')::numeric as price,
  nullif(freight_value,'')::numeric as freight_value
from {{ source('olist', 'order_items') }}
