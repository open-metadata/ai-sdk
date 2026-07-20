with source as (
    select * from {{ source('raw_core_banking', 'accounts') }}
),
renamed as (
    select
        account_id,
        customer_id,
        lower(account_type) as account_type,
        product_code,
        opened_date::date as opened_date,
        closed_date::date as closed_date,
        lower(status) as status,
        balance::numeric(18,4) as balance,
        currency,
        branch_id,
        interest_rate::numeric(10,6) as interest_rate,
        credit_limit::numeric(18,4) as credit_limit,
        is_joint::boolean as is_joint,
        created_at::timestamp as created_at,
        updated_at::timestamp as updated_at
    from source
)
select * from renamed
