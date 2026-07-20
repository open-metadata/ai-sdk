with source as (
    select * from {{ source('raw_lending', 'loan_applications') }}
),
renamed as (
    select
        application_id,
        customer_id,
        product_code,
        applied_date,
        requested_amount,
        fico_at_application,
        annual_income,
        dti_ratio,
        lower(purpose) as purpose,
        lower(status) as status,
        decision_date,
        lower(denial_reason) as denial_reason,
        loan_officer_id,
        branch_id
    from source
)
select * from renamed
