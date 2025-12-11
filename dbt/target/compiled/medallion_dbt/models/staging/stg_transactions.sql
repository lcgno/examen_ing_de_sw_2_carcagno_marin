


with source as (
    select *
    from read_parquet(
        '/home/carca/wslDocumentos/Codigo/examen_ing_de_sw_2_carcagno_marin/data/clean/transactions_20251211_clean.parquet'
    )
)

-- TODO: Completar el modelo para que cree la tabla staging con los tipos adecuados segun el schema.yml.
select
    cast(transaction_id as varchar) as transaction_id,
    cast(customer_id as varchar) as customer_id,
    cast(amount as double) as amount,
    cast(lower(status) as varchar) as status,
    cast(transaction_ts as timestamp) as transaction_ts,
    cast(transaction_date as date) as transaction_date

from source