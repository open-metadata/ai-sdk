-- Illustrative amortization-style schedule per loan.
-- One row per loan per month from origination_date through min(maturity_date, current_date).
-- Opening balance decays linearly for simplicity; interest_portion / principal_portion are
-- derived from the (fixed) monthly_payment. Not a production amortization.

with loans as (
    select * from {{ ref('stg_lending__loans') }}
),

-- Generate a small numbers helper (0..359) using a staging table as a row source.
-- Using a known-sized staging model keeps this Redshift-compatible without UDFs.
numbers as (
    select
        row_number() over (order by 1) - 1 as n
    from {{ ref('stg_lending__loan_payments') }}
    limit 360
),

scheduled as (
    select
        l.loan_id,
        l.customer_id,
        l.product_code,
        l.principal,
        l.interest_rate,
        l.term_months,
        l.origination_date,
        l.maturity_date,
        l.monthly_payment,
        n.n as month_offset,
        cast({{ dbt.dateadd('month', 'n.n', 'l.origination_date') }} as date) as schedule_date
    from loans l
    inner join numbers n
        on n.n < l.term_months
       and cast({{ dbt.dateadd('month', 'n.n', 'l.origination_date') }} as date) <= least(
               coalesce(l.maturity_date, current_date),
               current_date
           )
)

select
    loan_id,
    customer_id,
    product_code,
    principal,
    interest_rate,
    term_months,
    origination_date,
    maturity_date,
    monthly_payment,
    month_offset,
    schedule_date,
    -- Linear decay of opening balance (illustrative only)
    round(
        principal * (1.0 - ({{ safe_divide('month_offset', 'term_months') }})),
        4
    ) as opening_balance,
    -- Interest portion = opening_balance * (annual_rate / 12)
    round(
        principal
        * (1.0 - ({{ safe_divide('month_offset', 'term_months') }}))
        * ({{ safe_divide('interest_rate', '12.0') }}),
        4
    ) as interest_portion,
    -- Principal portion = monthly_payment - interest_portion (floored at 0)
    greatest(
        round(
            monthly_payment
            - principal
              * (1.0 - ({{ safe_divide('month_offset', 'term_months') }}))
              * ({{ safe_divide('interest_rate', '12.0') }}),
            4
        ),
        0
    ) as principal_portion
from scheduled
