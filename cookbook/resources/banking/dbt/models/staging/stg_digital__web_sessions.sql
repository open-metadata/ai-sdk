with source as (
    select * from {{ source('raw_digital', 'web_sessions') }}
),
renamed as (
    select
        trim(session_id)           as session_id,
        trim(customer_id)          as customer_id,
        cast(started_at as timestamp)      as started_at,
        cast(ended_at as timestamp)        as ended_at,
        cast(duration_seconds as integer)  as duration_seconds,
        lower(device_type)         as device_type,
        browser,
        os,
        ip_address,
        user_agent,
        referrer,
        landing_page,
        cast(pages_viewed as integer)      as pages_viewed
    from source
)
select * from renamed
