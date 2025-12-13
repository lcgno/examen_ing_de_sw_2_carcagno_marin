
with base as (
    select * from {{ ref('stg_transactions') }}
)

-- TODO: Completar el modelo para que cree la tabla fct_customer_transactions con las metricas en schema.yml.
select
    cast(customer_id as int) as customer_id,
    count(*) as transaction_count,
    sum(amount) as total_amount_completed,
    sum(amount) as total_amount_all
from base
where status = 'completed'
group by customer_id
