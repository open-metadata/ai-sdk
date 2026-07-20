-- DQ defect (h): AML alerts should not reference closed accounts.
-- Returns AML alerts joined to accounts where the linked account has
-- status='closed'. The engineered every-50th-row of aml_alerts pointing at
-- closed accounts (~40 rows) will surface here.

select
    a.alert_id,
    a.customer_id,
    a.account_id,
    acc.status as account_status,
    a.alert_date
from {{ ref('stg_risk__aml_alerts') }} a
inner join {{ ref('stg_core_banking__accounts') }} acc
    on a.account_id = acc.account_id
where acc.status = 'closed'
