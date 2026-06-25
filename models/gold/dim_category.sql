{{ config(materialized='table', schema='youtube_gold') }}

select
    row_number() over (order by country_code, category_id) as category_key,
    country_code,
    category_id,
    category_name
from {{ ref('silver_youtube_categories') }}