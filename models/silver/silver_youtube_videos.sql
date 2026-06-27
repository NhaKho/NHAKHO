{{ config(materialized='table', schema='youtube_silver') }}

with source_data as (

    select *
    from {{ source('youtube_bronze', 'raw_youtube_videos') }}

),

cleaned as (

    select
        trim(video_id) as video_id,
        trim(title) as title,
        trim(channel_title) as channel_title,

        try_cast(category_id as integer) as category_id,
        upper(trim(country_code)) as country_code,

        cast(try_strptime(trending_date, '%y.%d.%m') as date) as trending_date,
        try_cast(publish_time as timestamp) as publish_time,

        coalesce(try_cast(views as bigint), 0) as views,
        coalesce(try_cast(likes as bigint), 0) as likes,
        coalesce(try_cast(dislikes as bigint), 0) as dislikes,
        coalesce(try_cast(comment_count as bigint), 0) as comment_count,

        try_cast(comments_disabled as boolean) as comments_disabled,
        try_cast(ratings_disabled as boolean) as ratings_disabled,
        try_cast(video_error_or_removed as boolean) as video_error_or_removed,

        nullif(trim(tags), '') as tags,
        nullif(trim(description), '') as description,
        thumbnail_link,

        date_diff(
            'hour',
            try_cast(publish_time as timestamp),
            cast(try_strptime(trending_date, '%y.%d.%m') as timestamp)
        ) as hours_to_trend,

        round(
            (coalesce(try_cast(likes as bigint), 0) * 100.0)
            / nullif(coalesce(try_cast(views as bigint), 0), 0),
            4
        ) as like_rate,

        round(
            (coalesce(try_cast(comment_count as bigint), 0) * 100.0)
            / nullif(coalesce(try_cast(views as bigint), 0), 0),
            4
        ) as comment_rate,

        round(
            (
                coalesce(try_cast(likes as bigint), 0)
                + coalesce(try_cast(comment_count as bigint), 0)
            ) * 100.0
            / nullif(coalesce(try_cast(views as bigint), 0), 0),
            4
        ) as engagement_rate,

        row_number() over (
            partition by
                trim(video_id),
                upper(trim(country_code)),
                cast(try_strptime(trending_date, '%y.%d.%m') as date)
            order by
                coalesce(try_cast(views as bigint), 0) desc,
                coalesce(try_cast(likes as bigint), 0) desc,
                coalesce(try_cast(comment_count as bigint), 0) desc
        ) as rn

    from source_data

    where video_id is not null
      and trim(video_id) <> ''
      and trim(video_id) <> '#NAME?'
      and title is not null
      and trim(title) <> ''
      and try_cast(views as bigint) >= 0
      and try_strptime(trending_date, '%y.%d.%m') is not null
      and try_cast(publish_time as timestamp) is not null

)

select
    video_id,
    title,
    channel_title,
    category_id,
    country_code,
    trending_date,
    publish_time,
    views,
    likes,
    dislikes,
    comment_count,
    comments_disabled,
    ratings_disabled,
    video_error_or_removed,
    tags,
    description,
    thumbnail_link,
    hours_to_trend,
    like_rate,
    comment_rate,
    engagement_rate

from cleaned
where rn = 1