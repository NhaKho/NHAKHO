{{ config(materialized='table', schema='youtube_gold') }}

with dates as (

    select distinct
        trending_date as date_day
    from {{ ref('silver_youtube_videos') }}
    where trending_date is not null

    union

    select distinct
        cast(publish_time as date) as date_day
    from {{ ref('silver_youtube_videos') }}
    where publish_time is not null

)

select
    row_number() over (order by date_day) as date_key,
    date_day,

    extract(year from date_day) as year,
    extract(month from date_day) as month,
    extract(day from date_day) as day,

    date_trunc('month', date_day) as month_start,
    date_trunc('week', date_day) as week_start,

    strftime(date_day, '%Y-%m') as year_month,
    strftime(date_day, '%A') as day_name

from dates
where date_day is not null