{% test id_valido(model, column_name) %}

"""
Test para verificar que el id utilizado sea válido. 
Se asume que un id es válido si se trata de un entero mayor a 1000.
"""

select
    {{ column_name }}
from {{ model }}
where {{ column_name }} > 1000 or {{ column_name }} is null

{% endtest %}
