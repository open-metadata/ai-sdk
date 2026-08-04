-- DQ defect (g): closed accounts must not carry a negative balance.
-- Returns rows where status = 'closed' AND balance < 0.
-- The engineered account in row ~57 with status='closed' and balance=-150.00
-- will surface here.

select
    account_id,
    customer_id,
    status,
    balance
from {{ ref('stg_core_banking__accounts') }}
where status = 'closed'
  and balance < 0
