{{ config(
    materialized='table',
    schema='youtube_gold'
) }}

select
    c.country_code,

    count(*) as trending_records,
    count(distinct f.video_key) as unique_videos,
    count(distinct f.channel_key) as unique_channels,
    count(distinct f.category_key) as unique_categories,

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

left join {{ ref('dim_country') }} c
    on f.country_key = c.country_key

group by
    c.country_code