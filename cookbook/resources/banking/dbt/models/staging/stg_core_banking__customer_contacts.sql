with source as (
    select * from {{ source('raw_core_banking', 'customer_contacts') }}
),
renamed as (
    select
        contact_id,
        customer_id,
        lower(contact_type) as contact_type,
        contact_value,
        cast(is_primary as boolean) as is_primary,
        cast(is_verified as boolean) as is_verified,
        cast(opt_out as boolean) as opt_out,
        cast(added_at as timestamp) as added_at
    from source
)
select * from renamed
