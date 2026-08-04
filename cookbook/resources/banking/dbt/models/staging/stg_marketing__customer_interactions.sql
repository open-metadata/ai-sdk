with source as (
    select * from {{ source('raw_marketing', 'customer_interactions') }}
),
renamed as (
    select
        trim(interaction_id)            as interaction_id,
        trim(customer_id)               as customer_id,
        nullif(trim(campaign_id), '')   as campaign_id,
        lower(channel)                  as channel,
        lower(topic)                    as topic,
        trim(employee_id)               as employee_id,
        cast(interaction_timestamp as timestamp) as interaction_timestamp,
        cast(duration_minutes as integer)       as duration_minutes,
        lower(outcome)                  as outcome,
        cast(satisfaction_score as integer)     as satisfaction_score,
        notes
    from source
)
select * from renamed
