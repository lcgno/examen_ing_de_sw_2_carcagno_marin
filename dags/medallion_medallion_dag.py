"""Airflow DAG that orchestrates the medallion pipeline."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pendulum
from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.operators.python import PythonOperator

# pylint: disable=import-error,wrong-import-position


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from include.transformations import (
    clean_daily_transactions,
)  # pylint: disable=wrong-import-position

RAW_DIR = BASE_DIR / "data/raw"
CLEAN_DIR = BASE_DIR / "data/clean"
QUALITY_DIR = BASE_DIR / "data/quality"
DBT_DIR = BASE_DIR / "dbt"
PROFILES_DIR = BASE_DIR / "profiles"
WAREHOUSE_PATH = BASE_DIR / "warehouse/medallion.duckdb"


def _build_env(ds_nodash: str) -> dict[str, str]:
    """Build environment variables needed by dbt commands."""
    env = os.environ.copy()
    env.update(
        {
            "DBT_PROFILES_DIR": str(PROFILES_DIR),
            "CLEAN_DIR": str(CLEAN_DIR),
            "DS_NODASH": ds_nodash,
            "DUCKDB_PATH": str(WAREHOUSE_PATH),
        }
    )
    return env


def _run_dbt_command(command: str, ds_nodash: str) -> subprocess.CompletedProcess:
    """Execute a dbt command and return the completed process."""
    env = _build_env(ds_nodash)
    return subprocess.run(
        [
            "dbt",
            command,
            "--project-dir",
            str(DBT_DIR),
        ],
        cwd=DBT_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

######################
# Propio  
######################
def _run_clean_data(ds_nodash: str) -> None:
    """Wrapper para transformar ds_nodash en datetime y así poder ejecutar la limpieza de datos."""
    execution_date = datetime.strptime(ds_nodash, "%Y%m%d").date()
    
    raw = RAW_DIR / f"transactions_{ds_nodash}.csv"
    if raw.exists():
        clean_daily_transactions(
            execution_date=execution_date,
            raw_dir=RAW_DIR,
            clean_dir=CLEAN_DIR
    )
    else:
        print(f"Raw file {raw} does not exist.")
        return

def _run_dbt_silver(ds_nodash: str) -> None:
    """Run dbt models to load clean parquet into DuckDB."""
    # Verificar que existe el parquet de Bronze
    parquet_file = CLEAN_DIR / f"transactions_{ds_nodash}_clean.parquet"
    if not parquet_file.exists():
        print(f"⚠️ Parquet no encontrado para {ds_nodash}, saltando dbt run...")
        return
    
    result = _run_dbt_command("run", ds_nodash)
    if result.returncode != 0:
        raise AirflowException(
            f"dbt run failed with exit code {result.returncode}:\n{result.stderr}"
        )

def _run_dbt_gold(ds_nodash: str) -> None:
    # Ejecutar dbt test
    result = _run_dbt_command("test", ds_nodash)
    
    QUALITY_DIR.mkdir(parents=True, exist_ok=True)
    output_file = QUALITY_DIR / f"dq_results_{ds_nodash}.json"
    
    dq_results = {
        "ds_nodash": ds_nodash,
        "status": "passed" if result.returncode == 0 else "failed",
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(dq_results, f, indent=2)
    
    if result.returncode != 0:
        raise AirflowException(
            f"dbt test falló."
        )


def build_dag() -> DAG:
    """Construct the medallion pipeline DAG with bronze/silver/gold tasks."""
    with DAG(
        description="Bronze/Silver/Gold medallion demo with pandas, dbt, and DuckDB",
        dag_id="medallion_pipeline",
        schedule="0 6 * * *",
        start_date=pendulum.datetime(2025, 12, 1, tz="UTC"),
        catchup=True,
        max_active_runs=1,
    ) as medallion_dag:

        ######################
        # Propio  
        ######################
        
        # 1. Bronze: Limpieza de datos
        bronze_task = PythonOperator(
            task_id="bronze",
            python_callable=_run_clean_data,
            op_kwargs={"ds_nodash": "{{ ds_nodash }}"},
        )

        silver_task = PythonOperator(
            task_id="silver",
            python_callable=_run_dbt_silver,
            op_kwargs={"ds_nodash": "{{ ds_nodash }}"},
        )

        gold_task = PythonOperator(
            task_id="gold",
            python_callable=_run_dbt_gold,
            op_kwargs={"ds_nodash": "{{ ds_nodash }}"},
        )

        bronze_task >> silver_task >> gold_task

    return medallion_dag


dag = build_dag()
