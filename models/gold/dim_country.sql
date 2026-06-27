{{ config(materialized='table', schema='youtube_gold') }}

with countries as (

    select distinct
        upper(trim(country_code)) as country_code

    from {{ ref('silver_youtube_videos') }}

    where country_code is not null

)

select
    row_number() over (order by country_code) as country_key,
    country_code

from countries