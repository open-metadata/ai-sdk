-- Loans enriched with last payment date and a derived delinquency bucket.

with loans as (
    select * from {{ ref('stg_lending__loans') }}
),

last_payment as (
    select
        loan_id,
        max(payment_date) as last_payment_date
    from {{ ref('stg_lending__loan_payments') }}
    where status = 'posted'
    group by loan_id
),

joined as (
    select
        l.loan_id,
        l.application_id,
        l.customer_id,
        l.product_code,
        l.principal,
        l.interest_rate,
        l.term_months,
        l.origination_date,
        l.maturity_date,
        l.first_payment_date,
        l.next_due_date,
        l.status,
        l.balance,
        l.monthly_payment,
        l.branch_id,
        lp.last_payment_date,
        case
            when l.status = 'charged_off' then 999
            when l.status = 'paid_off'    then 0
            when l.next_due_date is null  then 0
            else greatest({{ days_between('l.next_due_date', 'current_date') }}, 0)
        end as days_past_due
    from loans l
    left join last_payment lp on l.loan_id = lp.loan_id
)

select
    loan_id,
    application_id,
    customer_id,
    product_code,
    principal,
    interest_rate,
    term_months,
    origination_date,
    maturity_date,
    first_payment_date,
    next_due_date,
    status,
    balance,
    monthly_payment,
    branch_id,
    last_payment_date,
    days_past_due,
    case
        when status = 'charged_off'                 then 'charge_off'
        when days_past_due = 0                      then 'current'
        when days_past_due between 1 and 29         then 'dpd_1_29'
        when days_past_due between 30 and 59        then 'dpd_30_59'
        when days_past_due between 60 and 89        then 'dpd_60_89'
        when days_past_due >= 90                    then 'dpd_90_plus'
        else 'current'
    end as delinquency_bucket,
    {{ safe_divide('balance', 'principal') }} as balance_to_principal_ratio
from joined
