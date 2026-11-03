select
  review_id,
  order_id,
  nullif(review_score,'')::integer as review_score,
  review_comment_title,
  review_comment_message,
  nullif(review_creation_date,'')::timestamp as review_creation_date,
  nullif(review_answer_timestamp,'')::timestamp as review_answer_timestamp
from {{ source('olist', 'order_reviews') }}
