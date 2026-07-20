with source as (
    select * from {{ source('raw_transactions', 'transactions') }}
),
renamed as (
    select
        transaction_id,
        account_id,
        posted_at::timestamp as posted_at,
        amount::numeric(18,4) as amount,
        currency,
        lower(transaction_type) as transaction_type,
        merchant_id,
        description,
        is_reversal::boolean as is_reversal,
        lower(channel) as channel,
        running_balance::numeric(18,4) as running_balance,
        created_at::timestamp as created_at
    from source
)
select * from renamed
