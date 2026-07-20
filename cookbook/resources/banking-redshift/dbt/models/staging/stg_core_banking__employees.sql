with source as (
    select * from {{ source('raw_core_banking', 'employees') }}
),
renamed as (
    select
        employee_id,
        trim(first_name) as first_name,
        trim(last_name) as last_name,
        lower(email) as email,
        phone,
        hire_date::date as hire_date,
        termination_date::date as termination_date,
        lower(role) as role,
        branch_id,
        manager_id,
        salary_band,
        is_active::boolean as is_active
    from source
)
select * from renamed
