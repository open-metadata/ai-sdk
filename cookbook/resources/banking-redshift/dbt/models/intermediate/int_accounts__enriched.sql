-- Accounts enriched with account_type reference data and holder aggregates.

with accounts as (
    select * from {{ ref('stg_core_banking__accounts') }}
),

account_types as (
    select * from {{ ref('stg_core_banking__account_types') }}
),

holders_agg as (
    select
        account_id,
        count(*) as holder_count,
        listagg(customer_id, ',') within group (order by holder_order) as customer_ids
    from {{ ref('stg_core_banking__account_holders') }}
    where removed_at is null
    group by account_id
)

select
    a.account_id,
    a.customer_id,
    a.account_type,
    at.account_type_name,
    at.product_category,
    a.product_code,
    a.opened_date,
    a.closed_date,
    a.status,
    a.balance,
    a.currency,
    a.branch_id,
    a.interest_rate,
    a.credit_limit,
    a.is_joint,
    a.created_at,
    a.updated_at,
    coalesce(h.holder_count, 0) as holder_count,
    h.customer_ids,
    case
        when a.closed_date is null
            then {{ days_between('a.opened_date', 'current_date') }}
        else null
    end as days_open
from accounts a
left join account_types at on a.account_type = at.account_type_code
left join holders_agg h    on a.account_id   = h.account_id
