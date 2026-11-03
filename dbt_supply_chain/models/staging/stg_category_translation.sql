select
  product_category_name,
  product_category_name_english
from {{ source('olist', 'category_translation') }}
