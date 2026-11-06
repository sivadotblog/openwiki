"""Reference data refresh flow (Prefect 3). Sample source for the dpwiki prototype.

Pulls code sets from the vendor SFTP drop, validates them, and publishes to
lakehouse.silver.reference_codes. New pipelines use Prefect (see ADR-003).
"""

from prefect import flow, task
from prefect.tasks import exponential_backoff


@task(retries=4, retry_delay_seconds=exponential_backoff(backoff_factor=30))
def fetch_drop(run_date: str) -> list[str]:
    ...


@task
def validate(files: list[str]) -> list[str]:
    # Rejects files whose row count drops more than 20% from the previous drop.
    ...


@task
def publish(files: list[str]) -> int:
    # MERGE into lakehouse.silver.reference_codes on (code_system, code).
    ...


@flow(name="reference-data-refresh", log_prints=True, timeout_seconds=2 * 60 * 60)
def reference_data_refresh(run_date: str) -> int:
    files = fetch_drop(run_date)
    good = validate(files)
    return publish(good)
