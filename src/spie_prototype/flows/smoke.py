"""Smoke-test flow: a single no-op task.

Validates the Prefect environment end-to-end (server reachable, task scheduling,
dashboard visibility) before any real reduction code is exercised. Run with::

    python -m spie_prototype.flows.smoke
"""
from __future__ import annotations

from prefect import flow, get_run_logger, task


@task(name="No-op")
def noop_task(message: str) -> str:
    """Return its input; the point is that it shows up on the dashboard."""
    logger = get_run_logger()
    logger.info(f"noop received: {message}")
    return message


@flow(name="Smoke Test")
def smoke_flow(message: str = "hello from spie-prototype") -> str:
    """Run one no-op task and return its result."""
    logger = get_run_logger()
    result = noop_task(message)
    logger.info(f"smoke flow complete: {result}")
    return result


if __name__ == "__main__":
    smoke_flow()
