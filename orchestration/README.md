# orchestration

Pipelines for the data platform.

- `airflow/dags/`: Airflow 2 DAGs on the managed Airflow environment `dp-airflow-prod`.
  Existing tier-1 pipelines stay on Airflow until migrated.
- `prefect/`: Prefect 3 flows and deployments. All new pipelines start here (ADR-003).
  Flows run on the `dp-k8s-pool` Kubernetes work pool.

Connections (`databricks_default`, `snowflake_transform`) come from the secrets backend,
never from code. Ask in #dp-platform-help if a connection is missing.
