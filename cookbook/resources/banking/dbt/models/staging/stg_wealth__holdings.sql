with source as (
    select * from {{ source('raw_wealth', 'holdings') }}
),
renamed as (
    select
        trim(holding_id)            as holding_id,
        trim(investment_account_id) as investment_account_id,
        trim(security_id)           as security_id,
        {{ to_decimal('quantity', 18, 4) }}           as quantity,
        {{ to_decimal('cost_basis', 18, 4) }}         as cost_basis,
        cast(as_of_date as date)            as as_of_date,
        cast(acquired_date as date)         as acquired_date
    from source
)
select * from renamed
