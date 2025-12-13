

"""
Test para verificar que el id utilizado sea válido. 
Se asume que un id es válido si se trata de un entero mayor a 1000.
"""

select
    customer_id
from "medallion"."main"."fct_customer_transactions"
where customer_id > 1000 or customer_id is null

