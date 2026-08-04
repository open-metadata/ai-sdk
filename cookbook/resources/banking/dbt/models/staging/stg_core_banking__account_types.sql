with source as (
    select * from {{ source('raw_core_banking', 'account_types') }}
),
renamed as (
    select
        lower(account_type_code) as account_type_code,
        account_type_name,
        lower(product_category) as product_category
    from source
)
select * from renamed
