select geolocation_zip_code_prefix as zip_prefix,
 percentile_cont(0.5) within group (order by geolocation_lat) as latitude,
 percentile_cont(0.5) within group (order by geolocation_lng) as longitude,
 count(*) as coordinate_observations
from {{ ref('stg_geolocation') }}
where geolocation_lat between -34 and 6 and geolocation_lng between -74 and -34
group by 1
