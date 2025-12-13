# Entrega Examen Final - Ingeniería de Software II

**Alumnos:** Carcagno,Leandro; Marín Del Boca, José

## Introducción

El presente documento detalla la implementación de una pipeline de datos para procesar transacciones diarias. El objetivo es transformar datos crudos (CSV) en un modelo de datos analítico y confiable, listo para ser consumido por herramientas de Business Intelligence o equipos de ciencia de datos.

Para lograrlo, implementamos una arquitectura Medallion (Bronce, Silver
 y Gold) utilizando un stack de herramientas moderno y robusto, orquestado por **Apache Airflow** y con las transformaciones de datos a cargo de **dbt**.

## Arquitectura y Tecnologías

Nuestra solución se basa en los siguientes componentes:

-   **Orquestador:** Apache Airflow para definir, programar y monitorear los flujos de trabajo (DAGs).
-   **Transformación de Datos:** dbt (Data Build Tool) para modelar, transformar y testear los datos directamente en nuestro data warehouse.
-   **Data Warehouse:** DuckDB, una base de datos analítica en memoria, ideal para este tipo de procesamientos por su velocidad y facilidad de integración.
-   **Procesamiento en Python:** La librería `pandas` para las tareas de limpieza inicial de los datos.
-   **Contenerización:** Docker y Docker Compose para crear un entorno de desarrollo aislado, portable y reproducible.
-   **Integración Continua:** GitHub Actions para automatizar la revisión de la calidad del código Python con Pylint.

La arquitectura Medallion nos permite organizar el flujo de datos en tres capas lógicas:

1.  **Capa Bronce:** Contiene los datos en su estado más crudo, tras una limpieza muy básica.
2.  **Capa Silver
:** Los datos de la capa Bronce son transformados, estandarizados y enriquecidos. En esta capa tenemos datos de mayor calidad.
3.  **Capa Gold:** Contiene los datos agregados, listos para el análisis y con una visión orientada al negocio.

## Implementación de la Pipeline

La pipeline se define en el DAG de Airflow `medallion_pipeline`, que ejecuta secuencialmente las tres capas.

### 1. Capa Bronce: Ingesta y Limpieza

-   **Trigger:** El DAG se ejecuta diariamente, procesando el archivo de transacciones del día (ej: `transactions_20251201.csv`).
-   **Proceso:** La tarea `bronze` ejecuta un script de Python (`include/transformations.py`) que realiza las siguientes operaciones:
    1.  Lee el archivo CSV crudo desde el directorio `data/raw`.
    2.  **Estandariza los nombres de las columnas** (minúsculas, sin espacios).
    3.  **Elimina registros duplicados**.
    4.  **Normaliza la columna `status`**: Mapea los valores a un conjunto definido (`completed`, `pending`, `failed`).
    5.  **Valida y convierte el tipo de dato de la columna `amount`** a numérico.
    6.  **Elimina filas con valores nulos** en campos críticos como `transaction_id`, `customer_id`, `amount` y `status`.
    7.  **Crea una columna derivada `transaction_date`** a partir del timestamp `transaction_ts`.
-   **Salida:** El resultado es un archivo en formato **Parquet** (`.parquet`), más eficiente para el almacenamiento y la lectura, que se guarda en el directorio `data/clean`.

### 2. Capa Silver
: Estandarización en el Data Warehouse

-   **Proceso:** La tarea `silver` invoca a dbt para ejecutar el modelo `stg_transactions.sql`.
    1.  Lee el archivo Parquet generado en la capa Bronce.
    2.  **Realiza un `CAST` explícito** en cada columna para asegurar que los tipos de datos sean los correctos dentro de nuestro DWH (DuckDB), según lo definido en el `schema.yml` (ej: `varchar`, `double`, `timestamp`).
-   **Salida:** Una tabla `stg_transactions` en DuckDB, que representa la capa Silver
. Esta tabla contiene datos limpios, tipados y listos para ser transformados en modelos de negocio.

### 3. Capa Gold: Agregación y Métricas de Negocio

-   **Proceso:** Finalmente, la tarea `gold` ejecuta los tests de dbt y (en una implementación futura) materializaría los modelos de la capa de marts.
    -   El modelo principal de esta capa es `fct_customer_transactions.sql`.
    -   Este modelo lee los datos de la capa Silver
 (`stg_transactions`) y los **agrega a nivel de cliente**.
    -   Calcula métricas clave de negocio para cada cliente, como:
        -   `customer_id`: Identificador del cliente.
        -   `transaction_count`: Conteo de transacciones.
        -   `total_amount_completed`: Suma del monto de las transacciones completadas.
        -   `total_amount_all`: Suma del monto de todas las transacciones.
-   **Salida:** Una tabla `fct_customer_transactions` en DuckDB. Esta tabla está lista para ser explotada por herramientas de visualización o para análisis más complejos, proveyendo una vista agregada del comportamiento de los clientes.

## Calidad de Datos (Data Quality)

La confiabilidad de los datos es fundamental. Para asegurarla, hemos implementado tests de dbt que se ejecutan como parte de la pipeline en la tarea `gold`.

-   **Tests Estándar:** Utilizamos tests predefinidos de dbt como `not_null`, `unique`, y `accepted_values` para validar la integridad de las columnas clave en nuestros modelos.
-   **Tests Genéricos Personalizados:** Desarrollamos tests propios en la carpeta `tests/generic`:
    -   `id_valido.sql`: Un test para validar que los IDs (ej: `customer_id`) tengan un formato específico (en este caso, que sean numéricos).

Los resultados de estos tests se guardan en un archivo JSON en la carpeta `data/quality` para su posterior análisis.


## Ejecución del Proyecto

Para ejecutar la pipeline, los pasos son los siguientes:

1.  Construir y levantar los contenedores con `docker-compose up -d`.
2.  Acceder a la interfaz de Airflow (usualmente en `http://localhost:8080`).
3.  Activar el DAG `medallion_pipeline` y monitorear su ejecución.
