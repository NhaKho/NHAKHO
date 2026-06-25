{{ config(materialized='table', schema='youtube_gold') }}

select
    row_number() over (order by v.country_code, v.video_id) as video_key,
    v.video_id,
    v.country_code,
    v.title,
    v.category_id,
    c.category_name,
    v.tags,
    v.description,
    v.thumbnail_link
from (
    select distinct
        video_id,
        country_code,
        title,
        category_id,
        tags,
        description,
        thumbnail_link
    from {{ ref('silver_youtube_videos') }}
    where video_id is not null
) v
left join {{ ref('silver_youtube_categories') }} c
    on v.country_code = c.country_code
    and v.category_id = c.category_id