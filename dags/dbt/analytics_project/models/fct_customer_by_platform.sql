with raw_data as (
    select
        customer_id,
        platforms
    from {{ ref('stg_customer_raw') }}
),

normalized as (
    select
        customer_id,
        unnest(string_to_array(
            replace(replace(replace(platforms, '[', ''), ']', ''), '''', ''), ','
        )) as platform
    from raw_data
),

cleaned as (
    select
        trim(lower(platform)) as platform
    from normalized
),

agg as (
    select
        platform,
        count(*) as customer_count
    from cleaned
    group by platform
    order by customer_count desc
)

select * from agg