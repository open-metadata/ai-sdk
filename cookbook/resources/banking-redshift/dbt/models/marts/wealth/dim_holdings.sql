-- Holdings dimension enriched with customer attributes and portfolio context.
--
-- weight_in_portfolio_pct is the holding's market_value as a share of the
-- customer's total AUM. is_top_5_holding flags the customer's five largest
-- positions by market_value.
--
-- Grain: one row per holding_id.

{{ config(materialized='table') }}

with holdings as (
    select * from {{ ref('int_holdings__valued') }}
),

customers as (
    select
        customer_id,
        first_name,
        last_name,
        customer_segment
    from {{ ref('int_customers__360') }}
),

enriched as (
    select
        h.holding_id,
        h.investment_account_id,
        h.customer_id,
        c.first_name,
        c.last_name,
        c.customer_segment,
        h.security_id,
        h.ticker,
        h.security_name,
        h.asset_class,
        h.sector,
        h.current_price,
        h.quantity,
        h.cost_basis,
        h.market_value,
        h.unrealized_pnl,
        h.unrealized_return_pct,
        h.as_of_date,
        h.acquired_date,
        sum(h.market_value) over (partition by h.customer_id) as customer_total_aum,
        row_number() over (
            partition by h.customer_id
            order by h.market_value desc nulls last, h.holding_id
        ) as customer_holding_rank
    from holdings h
    left join customers c on h.customer_id = c.customer_id
)

select
    holding_id,
    investment_account_id,
    customer_id,
    first_name,
    last_name,
    customer_segment,
    security_id,
    ticker,
    security_name,
    asset_class,
    sector,
    current_price,
    quantity,
    cost_basis,
    market_value,
    unrealized_pnl,
    unrealized_return_pct,
    as_of_date,
    acquired_date,
    {{ safe_divide('market_value', 'customer_total_aum') }} as weight_in_portfolio_pct,
    case when customer_holding_rank <= 5 then true else false end as is_top_5_holding
from enriched
