{{ config(
    materialized='table',
    schema='youtube_silver'
) }}

select
    v.video_id,
    v.title,
    v.channel_title,

    v.category_id,
    coalesce(c.category_name, 'Unknown') as category_name,

    v.country_code,
    v.trending_date,
    v.publish_time,

    v.views,
    v.likes,
    v.dislikes,
    v.comment_count,

    v.like_rate,
    v.comment_rate,
    v.engagement_rate,

    v.comments_disabled,
    v.ratings_disabled,
    v.video_error_or_removed,

    v.tags,
    v.description,
    v.thumbnail_link

from {{ ref('silver_youtube_videos') }} v

left join {{ ref('silver_youtube_categories') }} c
    on v.country_code = c.country_code
    and v.category_id = c.category_id