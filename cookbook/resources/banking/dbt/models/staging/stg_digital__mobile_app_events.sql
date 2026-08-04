with source as (
    select * from {{ source('raw_digital', 'mobile_app_events') }}
),
renamed as (
    select
        trim(event_id)             as event_id,
        trim(customer_id)          as customer_id,
        lower(event_type)          as event_type,
        cast(event_timestamp as timestamp) as event_timestamp,
        device_os,
        device_model,
        app_version,
        {{ to_decimal('geo_latitude', 10, 6) }}      as geo_latitude,
        {{ to_decimal('geo_longitude', 10, 6) }}     as geo_longitude,
        trim(session_id)           as session_id,
        screen_name
    from source
)
select * from renamed
