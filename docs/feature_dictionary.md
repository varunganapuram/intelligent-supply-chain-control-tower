# Purchase-time feature contract

| Feature | Source / rule |
|---|---|
| item_value, freight_value | Independent order-item sums; payment totals excluded from predictors |
| weight_g, volume_cm3 | Sum of product weights / dimensions for order items |
| distance_km | Mean seller-to-customer great-circle distance per item |
| item_count, seller_count | Counts of checkout items and distinct sellers |
| promised_days | Promised delivery date - purchase date, in calendar days |
| purchase_month, purchase_weekday | Calendar attributes known at purchase |
| customer_state | Checkout customer geography |
| primary_seller_state | Seller on the first item by item ID |
| primary_category | Product category of that first item, English where translated |
| seller_prior_late_rate | Smoothed prior single-seller completed-delivery outcomes, strictly earlier delivery events |
| seller_prior_orders | Sum of prior completed eligible single-seller volumes for current sellers |

Numeric missing values are median-imputed; scaling and one-hot categories are fitted on training data only. Unknown categories are ignored by the encoder. No feature uses actual duration, carrier handoff, final status, reviews, payment completion or future outcomes. Labels and label timestamps are stored beside features for audit and never included in the allowlist.

Olist provides final extracted attributes, not versioned checkout events. The availability of original item assignments, prices, product metadata and delivery promises at purchase is an explicit modeling assumption. Validate it with transactional event history before production use.

Metadata fields `prediction_as_of`, `history_latest_outcome_at` and `label_known_at` support time audits. Test fixtures mutate future outcomes and verify earlier features stay unchanged. An outcome occurring exactly at a purchase timestamp is excluded from history.
