with source as (
    select * from {{ source('raw_core_banking', 'customer_addresses') }}
),
renamed as (
    select
        address_id,
        customer_id,
        lower(address_type) as address_type,
        address_line_1,
        address_line_2,
        city,
        state,
        postal_code,
        country,
        cast(is_primary as boolean) as is_primary,
        cast(effective_from as date) as effective_from,
        cast(effective_to as date) as effective_to
    from source
)
select * from renamed
