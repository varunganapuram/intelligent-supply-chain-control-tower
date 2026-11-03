{{ config(indexes=[{'columns':['order_id'],'unique':true}, {'columns':['purchase_date']}, {'columns':['primary_seller_id']}]) }}
with items as (
 select i.order_id, count(*) as item_count, count(distinct i.seller_id) as seller_count,
 sum(i.price) as item_value, sum(i.freight_value) as freight_value,
 sum(p.product_weight_g) as weight_g, sum(p.volume_cm3) as volume_cm3,
 min(i.shipping_limit_date) as first_shipping_limit,
 (array_agg(i.seller_id order by i.order_item_id))[1] as primary_seller_id,
 (array_agg(p.category order by i.order_item_id))[1] as primary_category,
 (array_agg(s.seller_state order by i.order_item_id))[1] as primary_seller_state,
 avg(6371*2*asin(sqrt(least(1.0,greatest(0.0,
 power(sin(radians(c.latitude-s.latitude)/2),2)+cos(radians(s.latitude))*cos(radians(c.latitude))*
 power(sin(radians(c.longitude-s.longitude)/2),2)))))) as distance_km
 from {{ ref('stg_order_items') }} i
 join {{ ref('stg_orders') }} o using (order_id)
 left join {{ ref('dim_customer') }} c using (customer_id)
 left join {{ ref('fct_order_item') }} p using (order_id,order_item_id)
 left join {{ ref('dim_seller') }} s on i.seller_id=s.seller_id
 group by 1
), payments as (
 select order_id, sum(payment_value) as payment_value, count(*) as payment_count
 from {{ ref('stg_order_payments') }} group by 1
), reviews as (
 select *, row_number() over(partition by order_id order by review_answer_timestamp desc nulls last,
 review_creation_date desc nulls last, review_id desc, review_score desc) as rn
 from {{ ref('stg_order_reviews') }}
), base as (
 select o.*, o.order_purchase_timestamp::date as purchase_date, c.customer_state,
 i.item_count,i.seller_count,i.item_value,i.freight_value,i.weight_g,i.volume_cm3,i.distance_km,
 i.first_shipping_limit,i.primary_seller_id,i.primary_category,i.primary_seller_state,
 p.payment_value,p.payment_count,r.review_score,
 (o.order_status='delivered' and o.order_delivered_customer_date is not null
 and o.order_estimated_delivery_date is not null and o.order_purchase_timestamp is not null
 and o.order_delivered_customer_date>=o.order_purchase_timestamp
 and o.order_estimated_delivery_date::date>=o.order_purchase_timestamp::date) as eligible_delivery
 from {{ ref('stg_orders') }} o
 left join {{ ref('dim_customer') }} c using (customer_id)
 left join items i using (order_id)
 left join payments p using (order_id)
 left join reviews r on o.order_id=r.order_id and r.rn=1
)
select *,
 case when eligible_delivery then (order_delivered_customer_date::date>order_estimated_delivery_date::date)::int end as is_late,
 case when eligible_delivery then extract(epoch from (order_delivered_customer_date-order_purchase_timestamp))/86400.0 end as delivery_days,
 case when eligible_delivery then greatest(0,order_delivered_customer_date::date-order_estimated_delivery_date::date) end as delay_days,
 order_estimated_delivery_date::date-order_purchase_timestamp::date as promised_days,
 extract(epoch from (order_delivered_carrier_date-order_purchase_timestamp))/86400.0 as handoff_days,
 extract(epoch from (order_delivered_customer_date-order_delivered_carrier_date))/86400.0 as transit_days,
 case when item_count=1 and seller_count=1 and order_delivered_carrier_date is not null
 then (order_delivered_carrier_date>first_shipping_limit)::int end as handoff_after_item_deadline
from base
