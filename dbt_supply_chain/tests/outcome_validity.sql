select order_id from {{ ref('fct_order') }}
where (is_late is not null and (not eligible_delivery or delivery_days<0 or promised_days<0))
 or (eligible_delivery and is_late is null)
 or (is_late not in (0,1))
 or item_value<0 or freight_value<0
