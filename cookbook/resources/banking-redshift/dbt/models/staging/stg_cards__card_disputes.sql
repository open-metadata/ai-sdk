with source as (
    select * from {{ source('raw_cards', 'card_disputes') }}
),
renamed as (
    select
        dispute_id,
        authorization_id,
        card_id,
        lower(dispute_reason) as dispute_reason,
        dispute_amount,
        opened_date,
        resolved_date,
        lower(status) as status,
        chargeback_amount
    from source
)
select * from renamed
