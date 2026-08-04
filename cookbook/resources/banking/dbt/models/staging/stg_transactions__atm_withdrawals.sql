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
        {{ to_decimal('amount', 18, 4) }} as amount,
        {{ to_decimal('fee_amount', 18, 4) }} as fee_amount,
        cast(withdrawn_at as timestamp) as withdrawn_at,
        cast(is_foreign as boolean) as is_foreign,
        network,
        parent_transaction_id
    from source
)
select * from renamed
