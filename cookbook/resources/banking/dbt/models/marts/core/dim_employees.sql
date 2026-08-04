-- Employee dimension. Wraps int_employees__org and adds the human-readable
-- branch_name and manager_name (resolved via self-join on manager_id).
-- Grain: one row per employee_id.

with employees as (
    select * from {{ ref('int_employees__org') }}
),

branches as (
    select
        branch_id,
        branch_name
    from {{ ref('stg_core_banking__branches') }}
),

managers as (
    select
        employee_id as manager_employee_id,
        first_name  as manager_first_name,
        last_name   as manager_last_name
    from employees
)

select
    e.employee_id,
    e.manager_id,
    e.first_name,
    e.last_name,
    e.email,
    e.phone,
    e.hire_date,
    e.termination_date,
    e.role,
    e.branch_id,
    b.branch_name,
    e.salary_band,
    e.is_active,
    e.level,
    e.manager_chain_path,
    nullif(trim(m.manager_first_name || ' ' || m.manager_last_name), '') as manager_name
from employees e
left join branches b on e.branch_id  = b.branch_id
left join managers m on e.manager_id = m.manager_employee_id
