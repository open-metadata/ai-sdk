with source as (
    select * from {{ source('raw_wealth', 'holdings') }}
),
renamed as (
    select
        trim(holding_id)            as holding_id,
        trim(investment_account_id) as investment_account_id,
        trim(security_id)           as security_id,
        quantity::numeric           as quantity,
        cost_basis::numeric         as cost_basis,
        as_of_date::date            as as_of_date,
        acquired_date::date         as acquired_date
    from source
)
select * from renamed
