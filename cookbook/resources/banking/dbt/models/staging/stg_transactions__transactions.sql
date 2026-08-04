with source as (
    select * from {{ source('raw_transactions', 'transactions') }}
),
renamed as (
    select
        transaction_id,
        account_id,
        cast(posted_at as timestamp) as posted_at,
        {{ to_decimal('amount', 18, 4) }} as amount,
        currency,
        lower(transaction_type) as transaction_type,
        merchant_id,
        description,
        cast(is_reversal as boolean) as is_reversal,
        lower(channel) as channel,
        {{ to_decimal('running_balance', 18, 4) }} as running_balance,
        cast(created_at as timestamp) as created_at
    from source
)
select * from renamed
