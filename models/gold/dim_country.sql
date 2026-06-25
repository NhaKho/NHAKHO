{{ config(materialized='table', schema='youtube_gold') }}

select
    row_number() over (order by country_code) as country_key,
    country_code
from (
    select distinct country_code
    from {{ ref('silver_youtube_videos') }}
    where country_code is not null
)