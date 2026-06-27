{{ config(
    materialized='table',
    schema='youtube_gold'
) }}

select
    -- Video
    video_id,
    title,
    channel_title,

    -- Category
    category_id,
    coalesce(category_name, 'Unknown') as category_name,

    -- Country
    country_code,

    -- Time
    publish_time,
    trending_date,

    extract(year from trending_date) as trending_year,
    extract(month from trending_date) as trending_month,
    extract(day from trending_date) as trending_day,
    extract(hour from publish_time) as publish_hour,
    extract(dow from publish_time) as publish_day_of_week,

    hours_to_trend,

    -- Metrics
    views,
    likes,
    dislikes,
    comment_count,

    like_rate,
    comment_rate,
    engagement_rate,

    -- Flags
    comments_disabled,
    ratings_disabled,
    video_error_or_removed,

    -- ML Target
    case
        when engagement_rate >= (
            select percentile_cont(0.75)
            within group (order by engagement_rate)
            from {{ ref('silver_youtube_enriched') }}
            where engagement_rate is not null
        )
        then 1
        else 0
    end as is_high_engagement

from {{ ref('silver_youtube_enriched') }}

where video_id is not null
  and country_code is not null
  and trending_date is not null
  and engagement_rate is not null