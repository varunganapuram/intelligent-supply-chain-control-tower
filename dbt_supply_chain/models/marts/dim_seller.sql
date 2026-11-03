select s.*, g.latitude, g.longitude from {{ ref('stg_sellers') }} s
left join {{ ref('dim_geography') }} g on s.seller_zip_code_prefix=g.zip_prefix
