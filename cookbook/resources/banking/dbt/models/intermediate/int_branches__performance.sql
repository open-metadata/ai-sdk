-- Branch-level rollups across accounts, deposits, loans and active employees.

with branches as (
    select * from {{ ref('stg_core_banking__branches') }}
),

accounts as (
    select * from {{ ref('stg_core_banking__accounts') }}
),

account_types as (
    select * from {{ ref('stg_core_banking__account_types') }}
),

accounts_enriched as (
    select
        a.account_id,
        a.branch_id,
        a.balance,
        atypes.product_category
    from accounts a
    left join account_types atypes on a.account_type = atypes.account_type_code
),

account_agg as (
    select
        branch_id,
        count(*) as account_count,
        sum(
            case
                when product_category in ('deposit', 'savings', 'checking') and balance > 0
                    then balance
                else 0
            end
        ) as total_deposits
    from accounts_enriched
    group by branch_id
),

customers as (
    select customer_id, branch_id
    from {{ ref('stg_core_banking__customers') }}
),

loans as (
    select * from {{ ref('stg_lending__loans') }}
),

loan_agg as (
    select
        c.branch_id,
        sum(l.principal) as total_loan_principal,
        count(l.loan_id) as loan_count
    from loans l
    inner join customers c on l.customer_id = c.customer_id
    group by c.branch_id
),

employee_agg as (
    select
        branch_id,
        count(*) as employee_count
    from {{ ref('stg_core_banking__employees') }}
    where is_active = true
    group by branch_id
)

select
    b.branch_id,
    b.branch_name,
    b.address_line_1,
    b.city,
    b.state,
    b.postal_code,
    b.country,
    b.region,
    b.phone,
    b.manager_employee_id,
    b.opened_date,
    b.closed_date,
    b.is_active,
    coalesce(a.account_count, 0)         as account_count,
    coalesce(a.total_deposits, 0)        as total_deposits,
    coalesce(l.total_loan_principal, 0)  as total_loan_principal,
    coalesce(l.loan_count, 0)            as loan_count,
    coalesce(e.employee_count, 0)        as employee_count
from branches b
left join account_agg a  on b.branch_id = a.branch_id
left join loan_agg l     on b.branch_id = l.branch_id
left join employee_agg e on b.branch_id = e.branch_id
