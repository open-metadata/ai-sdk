with source as (
    select * from {{ source('raw_cards', 'card_authorizations') }}
),
renamed as (
    select
        authorization_id,
        card_id,
        merchant_id,
        amount,
        currency,
        lower(auth_status) as auth_status,
        lower(decline_reason) as decline_reason,
        auth_timestamp,
        is_card_present,
        ip_address
    from source
)
select * from renamed
