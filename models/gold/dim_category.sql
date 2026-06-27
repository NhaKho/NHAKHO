{{ config(materialized='table', schema='youtube_gold') }}

with category_from_videos as (

    select distinct
        country_code,
        category_id
    from {{ ref('silver_youtube_videos') }}
    where country_code is not null
      and category_id is not null

),

category_lookup as (

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
    row_number() over (order by v.country_code, v.category_id) as category_key,
    v.country_code,
    v.category_id,
    coalesce(c.category_name, 'Unknown') as category_name

from category_from_videos v

left join category_lookup c
    on v.country_code = c.country_code
    and v.category_id = c.category_id