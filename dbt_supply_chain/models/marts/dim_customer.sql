select c.*, g.latitude, g.longitude from {{ ref('stg_customers') }} c
left join {{ ref('dim_geography') }} g on c.customer_zip_code_prefix=g.zip_prefix
