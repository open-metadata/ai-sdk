-- Per-card activity rollup combining authorizations and disputes.

with cards as (
    select * from {{ ref('stg_cards__cards') }}
),

auth_agg as (
    select
        card_id,
        count(*) as total_auths,
        sum(case when auth_status = 'approved' then 1 else 0 end) as approved_auths,
        sum(case when auth_status = 'declined' then 1 else 0 end) as declined_auths,
        max(auth_timestamp) as last_used_at
    from {{ ref('stg_cards__card_authorizations') }}
    group by card_id
),

dispute_agg as (
    select
        card_id,
        count(*) as dispute_count,
        sum(coalesce(chargeback_amount, 0)) as chargeback_amount_total
    from {{ ref('stg_cards__card_disputes') }}
    group by card_id
)

select
    c.card_id,
    c.customer_id,
    c.card_number_masked,
    c.product_code,
    c.issued_date,
    c.expires_date,
    c.status,
    c.credit_limit,
    c.linked_account_id,
    coalesce(a.total_auths, 0)            as total_auths,
    coalesce(a.approved_auths, 0)         as approved_auths,
    coalesce(a.declined_auths, 0)         as declined_auths,
    a.last_used_at,
    coalesce(d.dispute_count, 0)          as dispute_count,
    coalesce(d.chargeback_amount_total, 0) as chargeback_amount_total,
    {{ safe_divide('a.approved_auths', 'a.total_auths') }} as approval_rate
from cards c
left join auth_agg a    on c.card_id = a.card_id
left join dispute_agg d on c.card_id = d.card_id
