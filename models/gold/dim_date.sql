{{ config(materialized='table', schema='youtube_gold') }}

with dates as (
    select distinct trending_date as date_day
    from {{ ref('silver_youtube_videos') }}

    union

    select distinct cast(publish_time as date) as date_day
    from {{ ref('silver_youtube_videos') }}
)

select
    row_number() over (order by date_day) as date_key,
    date_day,
    extract(year from date_day) as year,
    extract(month from date_day) as month,
    extract(day from date_day) as day,
    date_trunc('month', date_day) as month_start
from dates
where date_day is not null