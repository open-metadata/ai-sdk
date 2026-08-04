with source as (
    select * from {{ source('raw_risk', 'kyc_checks') }}
),
renamed as (
    select
        kyc_id,
        customer_id,
        lower(check_type) as check_type,
        check_date,
        lower(check_status) as check_status,
        lower(verification_method) as verification_method,
        documents_provided,
        performed_by_employee_id,
        next_review_date,
        lower(risk_assessment_band) as risk_assessment_band,
        created_at
    from source
)
select * from renamed
