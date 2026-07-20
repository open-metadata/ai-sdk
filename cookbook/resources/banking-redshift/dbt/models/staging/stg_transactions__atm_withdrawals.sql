with source as (
    select * from {{ source('raw_transactions', 'atm_withdrawals') }}
),
renamed as (
    select
        atm_withdrawal_id,
        account_id,
        atm_terminal_id,
        atm_city,
        atm_state,
        amount::numeric(18,4) as amount,
        fee_amount::numeric(18,4) as fee_amount,
        withdrawn_at::timestamp as withdrawn_at,
        is_foreign::boolean as is_foreign,
        network,
        parent_transaction_id
    from source
)
select * from renamed
