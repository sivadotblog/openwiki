"""Daily orders ingest: landing zone -> Databricks silver -> Snowflake gold.

Sample source for the OpenWiki demo.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.databricks.operators.databricks import DatabricksRunNowOperator
from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator
from airflow.sensors.filesystem import FileSensor

DEFAULT_ARGS = {
    "owner": "data-platform-eng",
    "retries": 3,
    "retry_delay": timedelta(minutes=10),
    "sla": timedelta(hours=4),
    "email_on_failure": False,
}

with DAG(
    dag_id="orders_ingest",
    start_date=datetime(2025, 1, 1),
    schedule="30 5 * * *",  # 05:30 UTC daily
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["orders", "tier-1"],
) as dag:
    wait_for_landing = FileSensor(
        task_id="wait_for_landing",
        filepath="/landing/orders/{{ ds }}/_SUCCESS",
        poke_interval=300,
        timeout=60 * 60 * 3,
        mode="reschedule",
    )

    silver_orders = DatabricksRunNowOperator(
        task_id="silver_orders",
        databricks_conn_id="databricks_default",
        job_name="silver_orders_merge",
        notebook_params={"run_date": "{{ ds }}"},
    )

    gold_daily_revenue = SnowflakeOperator(
        task_id="gold_daily_revenue",
        snowflake_conn_id="snowflake_transform",
        warehouse="TRANSFORM_WH",
        sql="CALL GOLD.BUILD_DAILY_REVENUE('{{ ds }}');",
    )

    wait_for_landing >> silver_orders >> gold_daily_revenue
