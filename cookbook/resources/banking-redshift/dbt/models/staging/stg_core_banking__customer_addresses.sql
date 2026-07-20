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
        is_primary::boolean as is_primary,
        effective_from::date as effective_from,
        effective_to::date as effective_to
    from source
)
select * from renamed
