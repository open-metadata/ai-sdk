-- DQ defect (e): customer addresses with an empty (whitespace-only) city.
-- Returns rows where city is the empty string. The not_null test catches
-- NULLs; this catches the engineered "" empty-city row in customer_addresses.

select
    address_id,
    customer_id,
    city
from {{ ref('stg_core_banking__customer_addresses') }}
where city is not null
  and trim(city) = ''
