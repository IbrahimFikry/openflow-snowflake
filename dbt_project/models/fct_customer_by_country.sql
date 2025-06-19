-- models/fct_customer_by_country.sql

with customers as (
    select *
    from {{ ref('stg_customer_raw') }}
),

agg as (
    select
        country,
        count(*) as customer_count
    from customers
    group by country
)

select * from agg
