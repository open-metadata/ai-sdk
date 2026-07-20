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
        opened_date::date as opened_date,
        closed_date::date as closed_date,
        is_active::boolean as is_active
    from source
)
select * from renamed
