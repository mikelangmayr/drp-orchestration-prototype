"""Prefect task wrappers for FITS I/O primitives."""
from __future__ import annotations

import numpy as np
from astropy.io import fits
from prefect import get_run_logger, task

from spie_prototype.core.io import discover_fits, load_flat_frame, save_edges
from spie_prototype.tasks._caching import (
    CACHE_EXPIRATION,
    DEFAULT_CACHE_KEY_FN,
    IO_RETRIES,
    IO_RETRY_DELAY_SECONDS,
)


@task(name="Discover FITS Frames", retries=IO_RETRIES, retry_delay_seconds=IO_RETRY_DELAY_SECONDS)
def discover_fits_task(input_dir: str, recursive: bool = False) -> list[str]:
    """List FITS frames in ``input_dir`` as a visible fan-out node.

    Matches gzipped frames too; set ``recursive=True`` for KOA carts that nest
    frames in subdirectories. Not cached: the output reflects current filesystem
    state, not just the path argument, so caching it would mask newly arrived
    frames.
    """
    logger = get_run_logger()
    paths = discover_fits(input_dir, recursive=recursive)
    logger.info(f"Discovered {len(paths)} FITS frames in {input_dir} (recursive={recursive})")
    return paths


@task(
    name="Load Flat Frame",
    cache_key_fn=DEFAULT_CACHE_KEY_FN,
    cache_expiration=CACHE_EXPIRATION,
    persist_result=True,
    retries=IO_RETRIES,
    retry_delay_seconds=IO_RETRY_DELAY_SECONDS,
)
def load_flat_frame_task(path: str, hdu: int = 0) -> tuple[np.ndarray, fits.Header]:
    """Load a FITS frame; cached by path so re-runs hit cache when files are unchanged."""
    logger = get_run_logger()
    logger.info(f"Loading {path} (hdu={hdu})")
    data, header = load_flat_frame(path, hdu=hdu)
    logger.info(f"Loaded shape={data.shape}, dtype={data.dtype}")
    return data, header


@task(name="Save Slit Edges", retries=IO_RETRIES, retry_delay_seconds=IO_RETRY_DELAY_SECONDS)
def save_edges_task(left_edges: np.ndarray, right_edges: np.ndarray, output_path: str) -> str:
    """Persist traced slit edges; not cached because the write is the point."""
    logger = get_run_logger()
    written = save_edges(left_edges, right_edges, output_path)
    logger.info(f"Saved {left_edges.shape[0]} slit edges to {written}")
    return written
