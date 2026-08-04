-- Trade activity rolled up per customer x asset_class x month.
--
-- Joins trades to investment_accounts (for customer_id) and securities
-- (for asset_class). Cancelled trades are kept — filter downstream if needed.
--
-- Grain: (customer_id, asset_class, period_month).

{{ config(materialized='table') }}

with trades as (
    select * from {{ ref('stg_wealth__trades') }}
),

investment_accounts as (
    select
        investment_account_id,
        customer_id
    from {{ ref('stg_wealth__investment_accounts') }}
),

securities as (
    select
        security_id,
        asset_class
    from {{ ref('stg_wealth__securities') }}
),

joined as (
    select
        ia.customer_id,
        s.asset_class,
        cast({{ dbt.date_trunc('month', 't.trade_timestamp') }} as date) as period_month,
        t.quantity,
        t.trade_price,
        t.commission,
        t.side
    from trades t
    left join investment_accounts ia on t.investment_account_id = ia.investment_account_id
    left join securities s           on t.security_id           = s.security_id
)

select
    customer_id,
    asset_class,
    period_month,
    count(*)                                                                 as trade_count,
    sum(quantity * trade_price)                                              as total_volume,
    sum(commission)                                                          as total_commission,
    sum(case when side = 'buy'  then 1 else 0 end)                           as buy_count,
    sum(case when side = 'sell' then 1 else 0 end)                           as sell_count,
    sum(quantity * case when side = 'buy' then 1 else -1 end)                as net_quantity
from joined
group by customer_id, asset_class, period_month
