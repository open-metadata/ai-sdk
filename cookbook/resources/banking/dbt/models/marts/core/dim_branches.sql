-- Branch dimension. Wraps int_branches__performance and resolves the branch
-- manager's name. Preference order: the manager_employee_id recorded on the
-- branch record; fallback to an employee at the branch with role='branch_manager'.
-- Grain: one row per branch_id.

with branches as (
    select * from {{ ref('int_branches__performance') }}
),

employees as (
    select
        employee_id,
        branch_id,
        role,
        first_name,
        last_name
    from {{ ref('int_employees__org') }}
),

branch_manager_by_role as (
    select branch_id, first_name, last_name
    from (
        select
            branch_id,
            first_name,
            last_name,
            row_number() over (
                partition by branch_id
                order by employee_id
            ) as rn
        from employees
        where role = 'branch_manager'
    ) ranked
    where rn = 1
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
    coalesce(
        nullif(trim(e.first_name || ' ' || e.last_name), ''),
        nullif(trim(bm.first_name || ' ' || bm.last_name), '')
    ) as branch_manager_name,
    b.opened_date,
    b.closed_date,
    b.is_active,
    b.account_count,
    b.total_deposits,
    b.total_loan_principal,
    b.loan_count,
    b.employee_count
from branches b
left join employees e             on b.manager_employee_id = e.employee_id
left join branch_manager_by_role bm on b.branch_id          = bm.branch_id
