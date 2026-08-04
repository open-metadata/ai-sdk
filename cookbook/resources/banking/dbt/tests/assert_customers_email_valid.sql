-- DQ defect (b): customers with invalid email format.
-- Returns rows where email does NOT match a basic RFC 5322-style pattern.
-- The engineered "not-an-email" row on CUST_000012 will surface here.

select
    customer_id,
    email
from {{ ref('stg_core_banking__customers') }}
where email is not null
  and email !~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
