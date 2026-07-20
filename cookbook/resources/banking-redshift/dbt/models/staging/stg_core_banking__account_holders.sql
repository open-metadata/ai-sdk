with source as (
    select * from {{ source('raw_core_banking', 'account_holders') }}
),
renamed as (
    select
        holder_id,
        account_id,
        customer_id,
        holder_order::integer as holder_order,
        lower(relationship) as relationship,
        added_at::timestamp as added_at,
        removed_at::timestamp as removed_at
    from source
)
select * from renamed
