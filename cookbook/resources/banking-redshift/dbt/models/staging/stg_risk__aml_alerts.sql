with source as (
    select * from {{ source('raw_risk', 'aml_alerts') }}
),
renamed as (
    select
        alert_id,
        customer_id,
        account_id,
        transaction_id,
        lower(alert_type) as alert_type,
        lower(severity) as severity,
        lower(status) as status,
        alert_date,
        triaged_date,
        closed_date,
        assigned_to_employee_id,
        narrative,
        scenario_code,
        created_at
    from source
)
select * from renamed
