-- Employee org hierarchy built with a recursive CTE.
-- Each employee row carries the chain of managers and the level (CEO = 0).

with recursive employees as (
    select * from {{ ref('stg_core_banking__employees') }}
),

org_tree (
    employee_id,
    manager_id,
    first_name,
    last_name,
    email,
    phone,
    hire_date,
    termination_date,
    role,
    branch_id,
    salary_band,
    is_active,
    level,
    manager_chain_path
) as (
    -- Anchor: top-level employees (no manager)
    select
        employee_id,
        manager_id,
        first_name,
        last_name,
        email,
        phone,
        hire_date,
        termination_date,
        role,
        branch_id,
        salary_band,
        is_active,
        0 as level,
        cast(first_name || ' ' || last_name as varchar(4096)) as manager_chain_path
    from employees
    where manager_id is null

    union all

    -- Recursive: walk down the org tree
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
        e.salary_band,
        e.is_active,
        o.level + 1 as level,
        cast(o.manager_chain_path || ' -> ' || e.first_name || ' ' || e.last_name as varchar(4096))
            as manager_chain_path
    from employees e
    inner join org_tree o on e.manager_id = o.employee_id
)

select
    employee_id,
    manager_id,
    first_name,
    last_name,
    email,
    phone,
    hire_date,
    termination_date,
    role,
    branch_id,
    salary_band,
    is_active,
    level,
    manager_chain_path
from org_tree
