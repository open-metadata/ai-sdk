with source as (
    select * from {{ source('raw_core_banking', 'accounts') }}
),
renamed as (
    select
        account_id,
        customer_id,
        lower(account_type) as account_type,
        product_code,
        cast(opened_date as date) as opened_date,
        cast(closed_date as date) as closed_date,
        lower(status) as status,
        {{ to_decimal('balance', 18, 4) }} as balance,
        currency,
        branch_id,
        {{ to_decimal('interest_rate', 10, 6) }} as interest_rate,
        {{ to_decimal('credit_limit', 18, 4) }} as credit_limit,
        cast(is_joint as boolean) as is_joint,
        cast(created_at as timestamp) as created_at,
        cast(updated_at as timestamp) as updated_at
    from source
)
select * from renamed
