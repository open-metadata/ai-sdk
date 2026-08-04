with source as (
    select * from {{ source('raw_lending', 'loans') }}
),
renamed as (
    select
        loan_id,
        application_id,
        customer_id,
        product_code,
        principal,
        interest_rate,
        term_months,
        origination_date,
        maturity_date,
        first_payment_date,
        next_due_date,
        lower(status) as status,
        balance,
        monthly_payment,
        branch_id,
        days_past_due,
        ifrs9_stage,
        pd_12m,
        lgd,
        ead,
        ecl_amount
    from source
)
select * from renamed
