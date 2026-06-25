{{ config(
    materialized='table',
    schema='youtube_silver'
) }}

select distinct

    cast(category_id as bigint) as category_id,

    trim(category_name) as category_name,

    upper(trim(country_code)) as country_code

from {{ source('youtube_bronze', 'raw_youtube_categories') }}

where category_id is not null
    and category_name is not null