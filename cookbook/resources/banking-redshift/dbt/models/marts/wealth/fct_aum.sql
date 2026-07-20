-- Assets Under Management (AUM) per customer.
--
-- Holdings are a single snapshot in this demo, so we anchor every row to the
-- current month via date_trunc('month', current_date). The shape is still
-- (customer_id, period_month) so downstream dashboards can plug into a
-- time-series spine when richer history is loaded.
--
-- Grain: (customer_id, period_month).

{{ config(materialized='table') }}

with holdings as (
    select * from {{ ref('int_holdings__valued') }}
    where customer_id is not null
)

select
    customer_id,
    cast(date_trunc('month', current_date) as date) as period_month,
    sum(market_value)                                as aum,
    sum(cost_basis)                                  as aum_cost_basis,
    sum(unrealized_pnl)                              as unrealized_pnl,
    count(distinct security_id)                      as holding_count
from holdings
group by customer_id
