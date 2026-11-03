select d::date as date_key, extract(year from d)::int as year,
 extract(month from d)::int as month, extract(isodow from d)::int as weekday,
 to_char(d,'YYYY-MM') as year_month
from generate_series('2016-01-01'::date,'2019-12-31'::date,'1 day') d
