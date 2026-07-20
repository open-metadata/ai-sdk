with source as (
    select * from {{ source('raw_core_banking', 'customers') }}
),
renamed as (
    select
        customer_id,
        trim(first_name) as first_name,
        trim(last_name) as last_name,
        lower(email) as email,
        phone,
        ssn,
        tax_id,
        date_of_birth::date as date_of_birth,
        customer_segment,
        lower(customer_type) as customer_type,
        branch_id,
        primary_employee_id,
        lower(kyc_status) as kyc_status,
        lower(risk_band) as risk_band,
        created_at::timestamp as created_at,
        updated_at::timestamp as updated_at
    from source
)
select * from renamed
