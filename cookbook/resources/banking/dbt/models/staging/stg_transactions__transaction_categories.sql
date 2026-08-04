with source as (
    select * from {{ source('raw_transactions', 'transaction_categories') }}
),
renamed as (
    select
        lower(category_code) as category_code,
        category_name,
        lower(category_group) as category_group,
        cast(sign_hint as integer) as sign_hint
    from source
)
select * from renamed
