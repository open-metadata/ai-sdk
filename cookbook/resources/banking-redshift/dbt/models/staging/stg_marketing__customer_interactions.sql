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
        interaction_timestamp::timestamp as interaction_timestamp,
        duration_minutes::integer       as duration_minutes,
        lower(outcome)                  as outcome,
        satisfaction_score::integer     as satisfaction_score,
        notes
    from source
)
select * from renamed
