select
  order_id,
  nullif(payment_sequential,'')::integer as payment_sequential,
  payment_type,
  nullif(payment_installments,'')::integer as payment_installments,
  nullif(payment_value,'')::numeric as payment_value
from {{ source('olist', 'order_payments') }}
