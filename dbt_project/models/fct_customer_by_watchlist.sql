-- models/fct_customer_by_watchlist.sql
with customers as (
    select
        customer_id,
        watchlist
    from {{ ref('stg_customer_raw') }}
),
    normalized as (
    select
        customer_id,
        unnest(string_to_array(
            replace(replace(replace(watchlist, '[', ''), ']', ''), '''', ''), ','
        )) as asset
    from customers
),

cleaned as (
    select
        trim(lower(asset)) as asset
    from normalized
),

agg as (
    select
        asset,
        count(*) as customer_count
    from cleaned
    group by asset
    order by customer_count desc
)

select * from agg
