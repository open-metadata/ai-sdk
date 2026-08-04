with source as (
    select * from {{ source('raw_core_banking', 'account_holders') }}
),
renamed as (
    select
        holder_id,
        account_id,
        customer_id,
        cast(holder_order as integer) as holder_order,
        lower(relationship) as relationship,
        cast(added_at as timestamp) as added_at,
        cast(removed_at as timestamp) as removed_at
    from source
)
select * from renamed
