# Source-to-target mapping

| source                                |    rows | staging                  | target                            |
|:--------------------------------------|--------:|:-------------------------|:----------------------------------|
| olist_orders_dataset.csv              |   99441 | stg_orders               | fct_order                         |
| olist_order_items_dataset.csv         |  112650 | stg_order_items          | fct_order_item / fct_order_seller |
| olist_customers_dataset.csv           |   99441 | stg_customers            | dim_customer                      |
| olist_sellers_dataset.csv             |    3095 | stg_sellers              | dim_seller                        |
| olist_products_dataset.csv            |   32951 | stg_products             | dim_product                       |
| olist_order_payments_dataset.csv      |  103886 | stg_order_payments       | Order payment aggregate           |
| olist_order_reviews_dataset.csv       |   99224 | stg_order_reviews        | Selected review on fct_order      |
| olist_geolocation_dataset.csv         | 1000163 | stg_geolocation          | dim_geography                     |
| product_category_name_translation.csv |      71 | stg_category_translation | dim_product.category              |

All raw columns load as text without changing original files. Staging SQL explicitly types timestamps, numeric amounts and dimensions. ZIP prefixes stay text to retain leading zeros.
