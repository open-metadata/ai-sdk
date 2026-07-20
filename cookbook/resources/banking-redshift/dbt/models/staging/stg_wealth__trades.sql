with source as (
    select * from {{ source('raw_wealth', 'trades') }}
),
renamed as (
    select
        trim(trade_id)              as trade_id,
        trim(investment_account_id) as investment_account_id,
        trim(security_id)           as security_id,
        lower(side)                 as side,
        quantity::numeric           as quantity,
        trade_price::numeric        as trade_price,
        commission::numeric         as commission,
        trade_timestamp::timestamp  as trade_timestamp,
        settle_date::date           as settle_date,
        lower(status)               as status,
        upper(venue)                as venue
    from source
)
select * from renamed
