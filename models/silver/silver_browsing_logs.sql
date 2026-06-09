{{ config(materialized='table') }}

WITH source_data AS (

    SELECT *
    FROM {{ source('main', 'browsing_behavior_logs') }}

),

cleaned AS (

    SELECT
        TRIM(session_id) AS session_id,
        TRIM(customer_id) AS customer_id,
        TRY_CAST("timestamp" AS TIMESTAMP) AS event_time,

        LOWER(TRIM(page_type)) AS page_type,
        NULLIF(TRIM(product_viewed), '') AS product_viewed,

        COALESCE(time_on_page_seconds, 0) AS time_on_page_seconds,
        COALESCE(clicks, 0) AS clicks,

        NULLIF(LOWER(TRIM(search_query)), '') AS search_query,
        LOWER(TRIM(device_type)) AS device_type,
        LOWER(TRIM(browser)) AS browser,
        LOWER(TRIM(operating_system)) AS operating_system,
        LOWER(TRIM(referrer_source)) AS referrer_source,

        ROW_NUMBER() OVER (
            PARTITION BY
                session_id,
                customer_id,
                "timestamp",
                page_type,
                product_viewed
            ORDER BY "timestamp"
        ) AS row_num

    FROM source_data

    WHERE session_id IS NOT NULL
      AND customer_id IS NOT NULL
      AND "timestamp" IS NOT NULL
      AND page_type IS NOT NULL
      AND TRIM(session_id) <> ''
      AND TRIM(customer_id) <> ''

)

SELECT
    session_id,
    customer_id,
    event_time,
    page_type,
    product_viewed,
    time_on_page_seconds,
    clicks,
    search_query,
    device_type,
    browser,
    operating_system,
    referrer_source
FROM cleaned
WHERE row_num = 1