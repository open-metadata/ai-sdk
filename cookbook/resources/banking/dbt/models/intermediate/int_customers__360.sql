-- One row per customer enriched with primary address, primary contacts,
-- latest KYC and most recent FICO score.

with customers as (
    select * from {{ ref('stg_core_banking__customers') }}
),

mailing_address as (
    select
        customer_id,
        mailing_address_line_1,
        mailing_address_line_2,
        mailing_city,
        mailing_state,
        mailing_postal_code,
        mailing_country
    from (
        select
            customer_id,
            address_line_1 as mailing_address_line_1,
            address_line_2 as mailing_address_line_2,
            city           as mailing_city,
            state          as mailing_state,
            postal_code    as mailing_postal_code,
            country        as mailing_country,
            row_number() over (
                partition by customer_id
                order by is_primary desc, effective_from desc
            ) as rn
        from {{ ref('stg_core_banking__customer_addresses') }}
        where address_type = 'mailing'
    ) ranked
    where rn = 1
),

contacts_pivoted as (
    select
        customer_id,
        max(case when contact_type = 'email'  and is_primary then contact_value end) as primary_email,
        max(case when contact_type = 'mobile' and is_primary then contact_value end) as primary_mobile
    from {{ ref('stg_core_banking__customer_contacts') }}
    group by customer_id
),

kyc_agg as (
    select
        customer_id,
        max(check_date) as last_kyc_date
    from {{ ref('stg_risk__kyc_checks') }}
    group by customer_id
),

kyc_last_status as (
    select customer_id, last_kyc_status
    from (
        select
            customer_id,
            check_status as last_kyc_status,
            row_number() over (
                partition by customer_id
                order by check_date desc
            ) as rn
        from {{ ref('stg_risk__kyc_checks') }}
    ) ranked
    where rn = 1
),

current_fico as (
    select
        customer_id,
        current_fico_score,
        current_fico_score_date,
        current_fico_bureau
    from (
        select
            customer_id,
            score_value as current_fico_score,
            score_date  as current_fico_score_date,
            bureau      as current_fico_bureau,
            row_number() over (
                partition by customer_id
                order by score_date desc
            ) as rn
        from {{ ref('stg_risk__credit_scores') }}
        where score_type = 'FICO'
    ) ranked
    where rn = 1
)

select
    c.customer_id,
    c.first_name,
    c.last_name,
    c.email,
    c.phone,
    c.ssn,
    c.date_of_birth,
    c.customer_segment,
    c.customer_type,
    c.branch_id,
    c.primary_employee_id,
    c.kyc_status,
    c.risk_band,
    c.created_at,
    c.updated_at,
    a.mailing_address_line_1,
    a.mailing_address_line_2,
    a.mailing_city,
    a.mailing_state,
    a.mailing_postal_code,
    a.mailing_country,
    cp.primary_email,
    cp.primary_mobile,
    k.last_kyc_date,
    ks.last_kyc_status,
    f.current_fico_score,
    f.current_fico_score_date,
    f.current_fico_bureau
from customers c
left join mailing_address a   on c.customer_id = a.customer_id
left join contacts_pivoted cp on c.customer_id = cp.customer_id
left join kyc_agg k           on c.customer_id = k.customer_id
left join kyc_last_status ks  on c.customer_id = ks.customer_id
left join current_fico f      on c.customer_id = f.customer_id
