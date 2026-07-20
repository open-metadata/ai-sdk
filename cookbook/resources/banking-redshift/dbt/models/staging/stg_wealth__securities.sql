with source as (
    select * from {{ source('raw_wealth', 'securities') }}
),
renamed as (
    select
        trim(security_id)     as security_id,
        upper(ticker)         as ticker,
        upper(isin)           as isin,
        name,
        lower(asset_class)    as asset_class,
        sector,
        upper(exchange)       as exchange,
        upper(currency)       as currency,
        current_price::numeric as current_price,
        price_as_of::date     as price_as_of
    from source
)
select * from renamed
