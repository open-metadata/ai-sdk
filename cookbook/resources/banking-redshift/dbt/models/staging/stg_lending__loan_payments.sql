with source as (
    select * from {{ source('raw_lending', 'loan_payments') }}
),
renamed as (
    select
        payment_id,
        loan_id,
        payment_date,
        amount,
        principal_portion,
        interest_portion,
        lower(payment_type) as payment_type,
        lower(status) as status,
        lower(channel) as channel,
        created_at
    from source
)
select * from renamed
