with source as (
    select * from {{ source('raw_core_banking', 'customer_contacts') }}
),
renamed as (
    select
        contact_id,
        customer_id,
        lower(contact_type) as contact_type,
        contact_value,
        is_primary::boolean as is_primary,
        is_verified::boolean as is_verified,
        opt_out::boolean as opt_out,
        added_at::timestamp as added_at
    from source
)
select * from renamed
