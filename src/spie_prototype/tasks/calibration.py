"""Prefect task wrappers for calibration primitives.

The two master-build tasks are the prototype's parallel calibration arms: they
are mutually independent, so the flow submits both and they run concurrently.
Being cached, they are also computed once and reused across every frame and
every re-run — the caching story the paper's claims 2 and 3 both lean on.
"""
from __future__ import annotations

import numpy as np
from prefect import get_run_logger, task

from spie_prototype.core.calibration import (
    combine_master_bias,
    make_master_bias,
    make_master_dark,
    subtract_bias,
    subtract_dark,
)
from spie_prototype.tasks._caching import CACHE_EXPIRATION, DEFAULT_CACHE_KEY_FN


@task(
    name="Build Master Bias",
    cache_key_fn=DEFAULT_CACHE_KEY_FN,
    cache_expiration=CACHE_EXPIRATION,
    persist_result=True,
    retries=0,  # deterministic compute
)
def make_master_bias_task(level: float = 0.0) -> float | np.ndarray:
    """Build the master bias (stub: a constant pedestal)."""
    logger = get_run_logger()
    logger.info(f"Building master bias (stub pedestal, level={level})")
    return make_master_bias(level)


@task(
    name="Combine Master Bias (ccdproc)",
    cache_key_fn=DEFAULT_CACHE_KEY_FN,
    cache_expiration=CACHE_EXPIRATION,
    persist_result=True,
    retries=0,  # deterministic compute
)
def combine_master_bias_task(frames: list[np.ndarray], method: str = "median") -> np.ndarray:
    """Combine real bias frames into a master bias via ccdproc (polyglot primitive)."""
    logger = get_run_logger()
    master = combine_master_bias(frames, method=method)
    logger.info(
        f"Combined {len(frames)} bias frames via ccdproc ({method}); "
        f"master shape={master.shape}, median={float(np.median(master)):.1f}"
    )
    return master


@task(
    name="Build Master Dark",
    cache_key_fn=DEFAULT_CACHE_KEY_FN,
    cache_expiration=CACHE_EXPIRATION,
    persist_result=True,
    retries=0,
)
def make_master_dark_task(level: float = 0.0) -> float | np.ndarray:
    """Build the master dark (stub: a constant level)."""
    logger = get_run_logger()
    logger.info(f"Building master dark (stub level={level})")
    return make_master_dark(level)


@task(
    name="Subtract Bias",
    cache_key_fn=DEFAULT_CACHE_KEY_FN,
    cache_expiration=CACHE_EXPIRATION,
    persist_result=True,
    retries=0,
)
def bias_subtract_task(frame: np.ndarray, master_bias: float | np.ndarray) -> np.ndarray:
    """Subtract the master bias from one frame."""
    logger = get_run_logger()
    corrected = subtract_bias(frame, master_bias)
    logger.info(f"Subtracted master bias: mean {float(frame.mean()):.1f} -> {float(corrected.mean()):.1f}")
    return corrected


@task(
    name="Subtract Dark",
    cache_key_fn=DEFAULT_CACHE_KEY_FN,
    cache_expiration=CACHE_EXPIRATION,
    persist_result=True,
    retries=0,
)
def dark_subtract_task(frame: np.ndarray, master_dark: float | np.ndarray) -> np.ndarray:
    """Subtract the master dark from one frame."""
    logger = get_run_logger()
    corrected = subtract_dark(frame, master_dark)
    logger.info(f"Subtracted master dark: mean {float(frame.mean()):.1f} -> {float(corrected.mean()):.1f}")
    return corrected
