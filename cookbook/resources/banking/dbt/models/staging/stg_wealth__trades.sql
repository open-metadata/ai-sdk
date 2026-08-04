with source as (
    select * from {{ source('raw_wealth', 'trades') }}
),
renamed as (
    select
        trim(trade_id)              as trade_id,
        trim(investment_account_id) as investment_account_id,
        trim(security_id)           as security_id,
        lower(side)                 as side,
        {{ to_decimal('quantity', 18, 4) }}           as quantity,
        {{ to_decimal('trade_price', 18, 4) }}        as trade_price,
        {{ to_decimal('commission', 18, 4) }}         as commission,
        cast(trade_timestamp as timestamp)  as trade_timestamp,
        cast(settle_date as date)           as settle_date,
        lower(status)               as status,
        upper(venue)                as venue
    from source
)
select * from renamed
