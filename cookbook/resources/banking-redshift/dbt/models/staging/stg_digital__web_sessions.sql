with source as (
    select * from {{ source('raw_digital', 'web_sessions') }}
),
renamed as (
    select
        trim(session_id)           as session_id,
        trim(customer_id)          as customer_id,
        started_at::timestamp      as started_at,
        ended_at::timestamp        as ended_at,
        duration_seconds::integer  as duration_seconds,
        lower(device_type)         as device_type,
        browser,
        os,
        ip_address,
        user_agent,
        referrer,
        landing_page,
        pages_viewed::integer      as pages_viewed
    from source
)
select * from renamed
