select
  product_id,
  product_category_name,
  nullif(product_name_lenght,'')::numeric as product_name_lenght,
  nullif(product_description_lenght,'')::numeric as product_description_lenght,
  nullif(product_photos_qty,'')::numeric as product_photos_qty,
  nullif(product_weight_g,'')::numeric as product_weight_g,
  nullif(product_length_cm,'')::numeric as product_length_cm,
  nullif(product_height_cm,'')::numeric as product_height_cm,
  nullif(product_width_cm,'')::numeric as product_width_cm
from {{ source('olist', 'products') }}
