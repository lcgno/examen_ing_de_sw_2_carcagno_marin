


with source as (
    select *
    from read_parquet(
        '/home/carca/wslDocumentos/Codigo/examen_ing_de_sw_2_carcagno_marin/data/clean/transactions_20251206_clean.parquet'
    )
)

-- TODO: Completar el modelo para que cree la tabla staging con los tipos adecuados segun el schema.yml.