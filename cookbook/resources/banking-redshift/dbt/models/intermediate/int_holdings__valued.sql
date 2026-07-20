-- Holdings priced at the current market price, with derived market value and
-- unrealized P&L. customer_id is propagated from investment_accounts so downstream
-- marts (e.g., fct_aum) can aggregate per customer.

with holdings as (
    select * from {{ ref('stg_wealth__holdings') }}
),

securities as (
    select * from {{ ref('stg_wealth__securities') }}
),

investment_accounts as (
    select
        investment_account_id,
        customer_id
    from {{ ref('stg_wealth__investment_accounts') }}
)

select
    h.holding_id,
    h.investment_account_id,
    ia.customer_id,
    h.security_id,
    s.ticker,
    s.name      as security_name,
    s.asset_class,
    s.sector,
    s.current_price,
    h.quantity,
    h.cost_basis,
    h.as_of_date,
    h.acquired_date,
    (h.quantity * s.current_price)                as market_value,
    (h.quantity * s.current_price) - h.cost_basis as unrealized_pnl,
    {{ safe_divide(
        '(h.quantity * s.current_price) - h.cost_basis',
        'h.cost_basis'
    ) }} as unrealized_return_pct
from holdings h
left join securities s           on h.security_id           = s.security_id
left join investment_accounts ia on h.investment_account_id = ia.investment_account_id
