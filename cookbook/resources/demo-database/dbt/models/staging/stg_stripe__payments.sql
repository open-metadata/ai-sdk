with source as (
    select * from {{ source('stripe', 'payments') }}
),

cleaned as (
    select
        id as payment_id,
        order_id,
        payment_method,
        amount as payment_amount,
        status as payment_status,
        created_at as payment_created_at,
        card_last_four,
        card_brand,
        billing_email,
        ip_address::text as ip_address,
        risk_score
    from source
    where id is not null
      and amount > 0
)

select * from cleaned
