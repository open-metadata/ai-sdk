with source as (
    select * from {{ source('raw_transactions', 'ach_transfers') }}
),
renamed as (
    select
        ach_id,
        account_id,
        lower(direction) as direction,
        amount::numeric(18,4) as amount,
        lower(ach_type) as ach_type,
        counterparty_routing,
        counterparty_account_masked,
        counterparty_name,
        settled_date::date as settled_date,
        originated_at::timestamp as originated_at,
        lower(status) as status,
        sec_code,
        return_reason_code,
        parent_transaction_id
    from source
)
select * from renamed
