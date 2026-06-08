{{ config(materialized='table') }}

WITH source_data AS (

    SELECT *
    FROM {{ source('main', 'bronze_orders') }}

),

cleaned AS (

    SELECT

        TRIM(order_id) AS order_id,
        TRIM(customer_id) AS customer_id,

        TRY_CAST(order_date AS TIMESTAMP) AS order_date,

        LOWER(TRIM(platform)) AS platform,

        TRY_CAST(order_value_ngn AS DOUBLE) AS order_value_ngn,
        TRY_CAST(shipping_fee_ngn AS DOUBLE) AS shipping_fee_ngn,

        LOWER(TRIM(payment_method)) AS payment_method,
        LOWER(TRIM(payment_processor)) AS payment_processor,

        LOWER(TRIM(delivery_city)) AS delivery_city,
        LOWER(TRIM(delivery_status)) AS delivery_status,

        TRY_CAST(estimated_delivery_days AS INTEGER)
            AS estimated_delivery_days,

        LOWER(TRIM(order_status)) AS order_status,

        ROW_NUMBER() OVER (
            PARTITION BY order_id
            ORDER BY TRY_CAST(order_date AS TIMESTAMP) DESC
        ) AS row_num

    FROM source_data

)

SELECT *
FROM cleaned

WHERE row_num = 1
  AND order_value_ngn > 0
  AND shipping_fee_ngn >= 0
  AND estimated_delivery_days >= 0
WHERE order_id IS NOT NULL
  AND customer_id IS NOT NULL
  AND order_date IS NOT NULL
  AND order_status IS NOT NULL
