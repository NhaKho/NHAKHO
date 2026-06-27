{{ config(
    materialized='table',
    schema='youtube_silver'
) }}

with source_data as (

    select *
    from {{ source('youtube_bronze', 'raw_youtube_categories') }}

),

cleaned as (

    select
        upper(trim(country_code)) as country_code,
        cast(category_id as integer) as category_id,
        nullif(trim(category_name), '') as category_name

    from source_data

    where category_id is not null
      and country_code is not null

),

deduplicated as (

    select
        country_code,
        category_id,
        coalesce(max(category_name), 'Unknown') as category_name

    from cleaned

    group by
        country_code,
        category_id

)

select *
from deduplicated