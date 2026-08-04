with source as (
    select * from {{ source('raw_core_banking', 'branches') }}
),
renamed as (
    select
        branch_id,
        trim(branch_name) as branch_name,
        address_line_1,
        city,
        state,
        postal_code,
        country,
        region,
        phone,
        manager_employee_id,
        cast(opened_date as date) as opened_date,
        cast(closed_date as date) as closed_date,
        cast(is_active as boolean) as is_active
    from source
)
select * from renamed
