with source as (
    select * from {{ source('raw_cards', 'cards') }}
),
renamed as (
    select
        card_id,
        customer_id,
        card_number_masked,
        product_code,
        issued_date,
        expires_date,
        lower(status) as status,
        credit_limit,
        linked_account_id
    from source
)
select * from renamed
