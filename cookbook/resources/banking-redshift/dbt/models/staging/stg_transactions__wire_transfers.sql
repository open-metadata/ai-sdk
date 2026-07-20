with source as (
    select * from {{ source('raw_transactions', 'wire_transfers') }}
),
renamed as (
    select
        wire_id,
        account_id,
        lower(direction) as direction,
        amount::numeric(18,4) as amount,
        currency,
        from_iban,
        to_iban,
        swift_code,
        fee_amount::numeric(18,4) as fee_amount,
        originator_name,
        beneficiary_name,
        wire_purpose,
        sent_at::timestamp as sent_at,
        lower(status) as status,
        parent_transaction_id
    from source
)
select * from renamed
