with source as (
    select * from {{ source('raw_digital', 'mobile_app_events') }}
),
renamed as (
    select
        trim(event_id)             as event_id,
        trim(customer_id)          as customer_id,
        lower(event_type)          as event_type,
        event_timestamp::timestamp as event_timestamp,
        device_os,
        device_model,
        app_version,
        geo_latitude::numeric      as geo_latitude,
        geo_longitude::numeric     as geo_longitude,
        trim(session_id)           as session_id,
        screen_name
    from source
)
select * from renamed
