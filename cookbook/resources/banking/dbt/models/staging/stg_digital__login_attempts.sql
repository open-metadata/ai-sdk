with source as (
    select * from {{ source('raw_digital', 'login_attempts') }}
),
renamed as (
    select
        trim(login_id)         as login_id,
        trim(customer_id)      as customer_id,
        cast(attempted_at as timestamp) as attempted_at,
        cast(success as boolean)       as success,
        lower(failure_reason)  as failure_reason,
        lower(channel)         as channel,
        ip_address,
        user_agent,
        lower(mfa_method)      as mfa_method,
        device_fingerprint
    from source
)
select * from renamed
