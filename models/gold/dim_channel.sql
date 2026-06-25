{{ config(materialized='table', schema='youtube_gold') }}

select
    row_number() over (order by country_code, channel_title) as channel_key,
    country_code,
    channel_title
from (
    select distinct
        country_code,
        channel_title
    from {{ ref('silver_youtube_videos') }}
    where channel_title is not null
)