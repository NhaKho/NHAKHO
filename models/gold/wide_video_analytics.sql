{{ config(
    materialized='table',
    schema='youtube_gold'
) }}

select

    -- Video
    v.video_id,
    v.title,
    v.channel_title,

    -- Category
    v.category_id,
    c.category_name,

    -- Country
    v.country_code,

    -- Time
    v.publish_time,
    v.trending_date,

    extract(year from v.trending_date) as trending_year,
    extract(month from v.trending_date) as trending_month,
    extract(day from v.trending_date) as trending_day,

    date_diff(
        'hour',
        v.publish_time,
        cast(v.trending_date as timestamp)
    ) as hours_to_trend,

    -- Metrics
    v.views,
    v.likes,
    v.dislikes,
    v.comment_count,

    v.like_rate,
    v.comment_rate,
    v.engagement_rate,

    -- Flags
    v.comments_disabled,
    v.ratings_disabled,
    v.video_error_or_removed,

    -- ML Target
    case
        when v.engagement_rate >= (
            select percentile_cont(0.75)
            within group (order by engagement_rate)
            from {{ ref('silver_youtube_videos') }}
        )
        then 1
        else 0
    end as is_high_engagement

from {{ ref('silver_youtube_videos') }} v

left join {{ ref('silver_youtube_categories') }} c
    on v.country_code = c.country_code
    and v.category_id = c.category_id