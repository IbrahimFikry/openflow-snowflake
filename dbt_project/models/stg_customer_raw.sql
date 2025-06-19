-- models/stg_customer_raw.sql
select *
from {{ source('public', 'stg_customer_raw') }}