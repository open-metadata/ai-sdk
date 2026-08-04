with source as (
    select * from {{ source('raw_cards', 'card_products') }}
),
renamed as (
    select
        product_code,
        product_name,
        lower(product_class) as product_class,
        annual_fee,
        credit_limit_band,
        is_active
    from source
)
select * from renamed
