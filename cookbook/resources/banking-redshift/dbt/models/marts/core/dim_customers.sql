-- Customer dimension enriched with rollup totals across deposits, loans and
-- wealth holdings, plus a value_segment bucket used by downstream marts.
-- Grain: one row per customer_id.

with customers as (
    select * from {{ ref('int_customers__360') }}
),

accounts as (
    select * from {{ ref('int_accounts__enriched') }}
),

loans as (
    select * from {{ ref('int_loans__delinquency') }}
),

holdings as (
    select * from {{ ref('int_holdings__valued') }}
),

deposit_agg as (
    select
        customer_id,
        sum(
            case
                when product_category = 'deposit' and balance > 0
                    then balance
                else 0
            end
        ) as total_deposit_balance,
        count(*) as account_count
    from accounts
    group by customer_id
),

loan_agg as (
    select
        customer_id,
        sum(
            case
                when status not in ('paid_off', 'charged_off') then balance
                else 0
            end
        ) as total_loan_balance,
        sum(
            case
                when status not in ('paid_off', 'charged_off') then 1
                else 0
            end
        ) as loan_count
    from loans
    group by customer_id
),

holdings_agg as (
    select
        customer_id,
        sum(market_value) as aum
    from holdings
    where customer_id is not null
    group by customer_id
),

joined as (
    select
        c.customer_id,
        c.first_name,
        c.last_name,
        c.email,
        c.phone,
        c.ssn,
        c.date_of_birth,
        c.customer_segment,
        c.customer_type,
        c.branch_id,
        c.primary_employee_id,
        c.kyc_status,
        c.risk_band,
        c.created_at,
        c.updated_at,
        c.mailing_address_line_1,
        c.mailing_address_line_2,
        c.mailing_city,
        c.mailing_state,
        c.mailing_postal_code,
        c.mailing_country,
        c.primary_email,
        c.primary_mobile,
        c.last_kyc_date,
        c.last_kyc_status,
        c.current_fico_score,
        c.current_fico_score_date,
        c.current_fico_bureau,
        coalesce(d.total_deposit_balance, 0) as total_deposit_balance,
        coalesce(d.account_count, 0)         as account_count,
        coalesce(l.total_loan_balance, 0)    as total_loan_balance,
        coalesce(l.loan_count, 0)            as loan_count,
        coalesce(h.aum, 0)                   as aum
    from customers c
    left join deposit_agg d  on c.customer_id = d.customer_id
    left join loan_agg l     on c.customer_id = l.customer_id
    left join holdings_agg h on c.customer_id = h.customer_id
)

select
    *,
    case
        when aum >= 250000                   then 'private_banking'
        when total_deposit_balance >= 50000  then 'high_value'
        when total_deposit_balance >= 5000   then 'mass_market'
        else 'emerging'
    end as value_segment
from joined
