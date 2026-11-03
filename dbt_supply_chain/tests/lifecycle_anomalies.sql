{{ config(severity='warn') }}
select order_id from {{ ref('fct_order') }} where
 order_delivered_carrier_date<order_purchase_timestamp or
 order_delivered_customer_date<order_delivered_carrier_date or
 order_approved_at<order_purchase_timestamp
