-- Loan delinquency snapshot rolled up by period x product x bucket.
-- NOTE: int_loans__delinquency only carries the current state of each loan,
-- so this mart emits a single snapshot row per (current_month, product, bucket).
-- npl_ratio is computed within (period_month, product_code).
-- Grain: (period_month, product_code, delinquency_bucket).

with loans as (
    select * from {{ ref('int_loans__delinquency') }}
),

snapshot_loans as (
    select
        date_trunc('month', current_date)::date as period_month,
        product_code,
        delinquency_bucket,
        balance
    from loans
    where status not in ('paid_off')
),

bucket_agg as (
    select
        period_month,
        product_code,
        delinquency_bucket,
        count(*)     as loan_count,
        sum(balance) as total_balance
    from snapshot_loans
    group by period_month, product_code, delinquency_bucket
),

product_total as (
    select
        period_month,
        product_code,
        sum(balance) as product_total_balance
    from snapshot_loans
    group by period_month, product_code
)

select
    b.period_month,
    b.product_code,
    b.delinquency_bucket,
    b.loan_count,
    b.total_balance,
    case
        when b.delinquency_bucket in ('dpd_90_plus', 'charge_off')
            then {{ safe_divide('b.total_balance', 'p.product_total_balance') }}
        else 0
    end as npl_ratio
from bucket_agg b
left join product_total p
    on b.period_month = p.period_month
    and b.product_code = p.product_code
