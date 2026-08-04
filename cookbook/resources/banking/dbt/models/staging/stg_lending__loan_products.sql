with source as (
    select * from {{ source('raw_lending', 'loan_products') }}
),
renamed as (
    select
        product_code,
        product_name,
        lower(product_class) as product_class,
        default_term_months,
        base_apr,
        min_amount,
        max_amount,
        is_secured,
        is_active
    from source
)
select * from renamed
