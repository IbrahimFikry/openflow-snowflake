-- models/fct_customer_by_month.sql

with customers as (
    select
        customer_id,
        account_created::date as created_date
    from {{ ref('stg_customer_raw') }}
),

monthly_agg as (
    select
        date_trunc('month', created_date) as registration_month,
        count(*) as customer_count
    from customers
    group by 1
    order by 1
)

select * from monthly_agg