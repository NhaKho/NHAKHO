{{ config(materialized='table', schema='youtube_gold') }}

with cleaned as (

    select distinct
        upper(trim(country_code)) as country_code,
        nullif(trim(channel_title), '') as channel_title
    from {{ ref('silver_youtube_videos') }}
    where channel_title is not null
      and country_code is not null

)

select
    row_number() over (order by country_code, channel_title) as channel_key,
    country_code,
    channel_title

from cleaned

where channel_title is not null