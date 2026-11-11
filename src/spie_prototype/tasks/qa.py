"""Prefect task wrapper for QA plotting primitives."""
from __future__ import annotations

import numpy as np
from prefect import get_run_logger, task

from spie_prototype.core.qa import generate_trace_qa_plot
from spie_prototype.tasks._caching import IO_RETRIES, IO_RETRY_DELAY_SECONDS


@task(name="Trace QA Plot", retries=IO_RETRIES, retry_delay_seconds=IO_RETRY_DELAY_SECONDS)
def generate_trace_qa_plot_task(
    data: np.ndarray,
    left_edges: np.ndarray,
    right_edges: np.ndarray,
    output_path: str,
    title: str = "Slit Trace QA",
) -> str:
    """Render the trace QA figure; not cached because the PNG write is the point."""
    logger = get_run_logger()
    written = generate_trace_qa_plot(data, left_edges, right_edges, output_path, title=title)
    logger.info(f"Wrote trace QA plot to {written}")
    return written
