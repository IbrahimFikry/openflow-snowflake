with raw_data as (
    select
        customer_id,
        replace(replace(replace(platforms, '[', ''), ']', ''), '''', '') as cleaned_platforms
    from {{ ref('stg_customer_raw') }}
),

split_platforms as (
    select
        customer_id,
        trim(lower(p)) as platform
    from raw_data,
    unnest(string_to_array(cleaned_platforms, ',')) as p
),

-- Count platform usage per platform
platform_usage as (
    select
        platform as platform_combination,
        count(distinct customer_id) as customer_count
    from split_platforms
    group by platform
),

-- Get platform combination per customer
platform_combinations as (
    select
        customer_id,
        array_agg(distinct platform order by platform) as used_platforms,
        count(distinct platform) as platform_count
    from split_platforms
    group by customer_id
),

-- Flag combinations
combination_flags as (
    select
        customer_id,
        case 
            when platform_count = 1 then 'single_platform'
            when platform_count = 2 and used_platforms = array['mobile', 'mt5'] then 'dual (mobile, mt5)'
            when platform_count = 2 and used_platforms = array['web', 'mobile'] then 'dual (web, mobile)'
            when platform_count = 2 and used_platforms = array['mt5', 'web'] then 'dual (web, mt5)'
            when platform_count = 3 then 'all_platforms'
        end as platform_combination
    from platform_combinations
),

-- Count platform combination usage
combination_summary as (
    select
        platform_combination,
        count(*) as customer_count
    from combination_flags
    where platform_combination is not null
    group by platform_combination
)

-- Final union of individual platform and combination summaries
select * from platform_usage
union all
select * from combination_summary
