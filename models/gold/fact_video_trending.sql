{{ config(materialized='table', schema='youtube_gold') }}

select
    dv.video_key,
    dc.country_key,
    dcat.category_key,
    dch.channel_key,
    dd.date_key as trending_date_key,

    v.video_id,
    v.country_code,
    v.category_id,
    v.category_name,
    v.channel_title,
    v.trending_date,

    v.views,
    v.likes,
    v.dislikes,
    v.comment_count,

    v.like_rate,
    v.comment_rate,
    v.engagement_rate,

    v.comments_disabled,
    v.ratings_disabled,
    v.video_error_or_removed

from {{ ref('silver_youtube_enriched') }} v

left join {{ ref('dim_video') }} dv
    on v.video_id = dv.video_id
    and v.country_code = dv.country_code

left join {{ ref('dim_country') }} dc
    on v.country_code = dc.country_code

left join {{ ref('dim_category') }} dcat
    on v.country_code = dcat.country_code
    and v.category_id = dcat.category_id

left join {{ ref('dim_channel') }} dch
    on v.country_code = dch.country_code
    and v.channel_title = dch.channel_title

left join {{ ref('dim_date') }} dd
    on v.trending_date = dd.date_day

where dv.video_key is not null
  and dc.country_key is not null
  and dcat.category_key is not null
  and dch.channel_key is not null
  and dd.date_key is not null