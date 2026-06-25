{{ config(
    materialized='table',
    schema='youtube_gold'
) }}

select
    d.year,
    d.month,
    c.country_code,
    cat.category_name,

    count(*) as trending_records,
    count(distinct f.video_key) as unique_videos,
    count(distinct f.channel_key) as unique_channels,

    sum(f.views) as total_views,
    sum(f.likes) as total_likes,
    sum(f.dislikes) as total_dislikes,
    sum(f.comment_count) as total_comments,

    round(avg(f.views), 2) as avg_views,
    round(avg(f.likes), 2) as avg_likes,
    round(avg(f.comment_count), 2) as avg_comments,

    round(avg(f.like_rate), 4) as avg_like_rate,
    round(avg(f.comment_rate), 4) as avg_comment_rate,
    round(avg(f.engagement_rate), 4) as avg_engagement_rate

from {{ ref('fact_video_trending') }} f

left join {{ ref('dim_date') }} d
    on f.trending_date_key = d.date_key

left join {{ ref('dim_country') }} c
    on f.country_key = c.country_key

left join {{ ref('dim_category') }} cat
    on f.category_key = cat.category_key

group by
    d.year,
    d.month,
    c.country_code,
    cat.category_name