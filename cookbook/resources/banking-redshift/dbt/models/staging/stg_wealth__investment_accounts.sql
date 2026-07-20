with source as (
    select * from {{ source('raw_wealth', 'investment_accounts') }}
),
renamed as (
    select
        trim(investment_account_id) as investment_account_id,
        trim(customer_id)            as customer_id,
        lower(account_type)          as account_type,
        opened_date::date            as opened_date,
        lower(status)                as status,
        lower(risk_tolerance)        as risk_tolerance,
        lower(investment_objective)  as investment_objective,
        trim(advisor_employee_id)    as advisor_employee_id,
        created_at::date             as created_at
    from source
)
select * from renamed
