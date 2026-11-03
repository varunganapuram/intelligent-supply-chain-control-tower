# Data quality and exclusions

No source files are edited. The profile records every null count, key duplicate count, exact duplicate count and file hash.

| check                           |   count |
|:--------------------------------|--------:|
| total_orders                    |   99441 |
| ineligible_punctuality          |    2971 |
| delivered_missing_actual        |       8 |
| carrier_before_purchase         |     166 |
| delivery_before_carrier         |      23 |
| approval_before_purchase        |       0 |
| multi_seller_orders             |    1278 |
| multi_item_orders               |    9803 |
| multi_payment_orders            |    2961 |
| distance_missing                |     775 |
| weight_missing                  |     791 |
| promised_missing                |       0 |
| missing_seller_refs             |       0 |
| missing_product_refs            |       0 |
| geolocation_outside_brazil_bbox |      42 |
| negative_item_amounts           |       0 |
| invalid_product_dimensions      |       4 |
| invalid_zip_prefixes            |       0 |

The 189 distinct lifecycle warnings comprise carrier-before-purchase and delivery-before-carrier anomalies. They are retained and reported. Order punctuality uses valid purchase/actual/promise dates; stage timing is a separate diagnostic and requires caution. Repeated geolocation rows are reduced by median coordinates after bounding-box validation; reviews are reduced deterministically to one selected record per order. Four nonpositive product dimensions/weights remain visible in diagnostics. No negative item amounts or missing seller/product references were found.
