{{ config(materialized='table', schema='youtube_gold') }}

with ranked_videos as (

    select
        video_id,
        country_code,
        title,
        channel_title,
        category_id,
        tags,
        description,
        thumbnail_link,
        publish_time,

        row_number() over (
            partition by video_id, country_code
            order by views desc, likes desc, comment_count desc, trending_date desc
        ) as rn

    from {{ ref('silver_youtube_videos') }}

    where video_id is not null
      and country_code is not null

),

categories as (

    select
        country_code,
        category_id,
        max(category_name) as category_name

    from {{ ref('silver_youtube_categories') }}

    group by
        country_code,
        category_id

)

select
    row_number() over (order by v.country_code, v.video_id) as video_key,

    v.video_id,
    v.country_code,
    v.title,
    v.channel_title,

    v.category_id,
    coalesce(c.category_name, 'Unknown') as category_name,

    v.tags,
    v.description,
    v.thumbnail_link,
    v.publish_time

from ranked_videos v

left join categories c
    on v.country_code = c.country_code
    and v.category_id = c.category_id

where v.rn = 1