with source as (
    select * from {{ source('raw_cards', 'merchants') }}
),
renamed as (
    select
        merchant_id,
        merchant_name,
        mcc_code,
        mcc_description,
        city,
        state,
        country,
        created_at
    from source
)
select * from renamed
