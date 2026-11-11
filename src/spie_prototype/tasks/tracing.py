"""Prefect task wrapper for the slit-tracing primitive."""
from __future__ import annotations

import numpy as np
from prefect import get_run_logger, task

from spie_prototype.core.tracing import DEFAULT_SPECTROGRAPH, trace_slits
from spie_prototype.tasks._caching import CACHE_EXPIRATION, DEFAULT_CACHE_KEY_FN


@task(
    name="Trace Slits (PypeIt)",
    cache_key_fn=DEFAULT_CACHE_KEY_FN,
    cache_expiration=CACHE_EXPIRATION,
    persist_result=True,
    retries=0,  # CPU-bound: failures are deterministic, retrying wastes time
)
def trace_slits_task(
    data: np.ndarray,
    spectrograph_name: str = DEFAULT_SPECTROGRAPH,
    fit_order: int = 5,
) -> tuple[np.ndarray, np.ndarray]:
    """Trace slit edges in a flat frame; returns ``(left_edges, right_edges)``.

    The raw ``EdgeTraceSet`` is intentionally dropped at the task boundary: it is
    not needed downstream, and arrays are what the cache and dashboard show.
    """
    logger = get_run_logger()
    logger.info(
        f"Tracing: shape={data.shape}, dtype={data.dtype}, "
        f"spectrograph={spectrograph_name}, fit_order={fit_order}"
    )
    left_edges, right_edges, _ = trace_slits(
        data, spectrograph_name=spectrograph_name, fit_order=fit_order
    )

    n_slits = left_edges.shape[0] if left_edges.size > 0 else 0
    if n_slits == 0:
        logger.warning("No slits found — check input frame and parameters")
    else:
        mid = left_edges.shape[1] // 2
        median_width = float(np.median(right_edges[:, mid] - left_edges[:, mid]))
        logger.info(f"Found {n_slits} slits, median width = {median_width:.1f} px")
    return left_edges, right_edges
