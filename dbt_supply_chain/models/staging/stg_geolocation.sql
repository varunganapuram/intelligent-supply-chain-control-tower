select
  geolocation_zip_code_prefix,
  nullif(geolocation_lat,'')::double precision as geolocation_lat,
  nullif(geolocation_lng,'')::double precision as geolocation_lng,
  geolocation_city,
  geolocation_state
from {{ source('olist', 'geolocation') }}
