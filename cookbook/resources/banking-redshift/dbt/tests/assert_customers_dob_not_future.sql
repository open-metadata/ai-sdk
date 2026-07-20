-- DQ defect (c): customers with a future-dated date_of_birth.
-- Returns rows where date_of_birth > current_date.
-- The engineered 2050-01-01 row on CUST_000013 will surface here.

select
    customer_id,
    date_of_birth
from {{ ref('stg_core_banking__customers') }}
where date_of_birth > current_date
