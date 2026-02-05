with source as (
    select * from {{ source('stripe', 'refunds') }}
),

cleaned as (
    select
        id as refund_id,
        payment_id,
        amount as refund_amount,
        reason as refund_reason,
        status as refund_status,
        created_at as refund_created_at
    from source
    where id is not null
)

select * from cleaned
