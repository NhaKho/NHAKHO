{{ config(materialized='table', schema='youtube_silver') }}

with source_data as (
    select *
    from {{ source('youtube_bronze', 'raw_youtube_videos') }}
),

cleaned as (
    select
        video_id,
        trim(title) as title,
        trim(channel_title) as channel_title,
        cast(category_id as integer) as category_id,
        upper(trim(country_code)) as country_code,

        cast(strptime(trending_date, '%y.%d.%m') as date) as trending_date,
        cast(publish_time as timestamp) as publish_time,

        coalesce(cast(views as bigint), 0) as views,
        coalesce(cast(likes as bigint), 0) as likes,
        coalesce(cast(dislikes as bigint), 0) as dislikes,
        coalesce(cast(comment_count as bigint), 0) as comment_count,

        cast(comments_disabled as boolean) as comments_disabled,
        cast(ratings_disabled as boolean) as ratings_disabled,
        cast(video_error_or_removed as boolean) as video_error_or_removed,

        nullif(trim(tags), '') as tags,
        nullif(trim(description), '') as description,
        thumbnail_link,

        date_diff('hour', cast(publish_time as timestamp), cast(strptime(trending_date, '%y.%d.%m') as timestamp)) as hours_to_trend,

        round((likes * 100.0) / nullif(views, 0), 4) as like_rate,
        round((comment_count * 100.0) / nullif(views, 0), 4) as comment_rate,
        round(((likes + comment_count) * 100.0) / nullif(views, 0), 4) as engagement_rate

    from source_data
    where video_id is not null
      and title is not null
      and views >= 0
)

select *
from cleaned