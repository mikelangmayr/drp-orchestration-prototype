"""Calibration primitives: master construction and frame correction.

Two kinds of master-bias construction live here:

- ``make_master_bias`` / ``make_master_dark`` — *stub* builders returning a
  constant pedestal, used when the prototype's synthetic flats have no matching
  bias/dark stack.
- ``combine_master_bias`` — a **real, polyglot primitive** sourced from
  ``ccdproc`` (an Astropy-coordinated package). It median-combines a stack of
  real bias frames into a master. This is the Phase 7 demonstration that the
  orchestration is primitive-*source*-agnostic: a ccdproc primitive composes in
  the same DAG as the PypeIt trace and our custom subtract steps (ADR 0008).

Masters are represented as either a scalar pedestal or a 2D frame; the subtract
primitives broadcast over both, so the stub→real upgrade needs no signature
change (as long as the master and the frame share a detector shape).
"""
from __future__ import annotations

import astropy.units as u
import numpy as np
from astropy.nddata import CCDData
from ccdproc import combine


def combine_master_bias(frames: list[np.ndarray], method: str = "median") -> np.ndarray:
    """Combine a stack of bias frames into a master bias using ``ccdproc``.

    A polyglot primitive: the combination is done by ccdproc (Astropy ecosystem),
    adapted to the ``core`` contract of numpy-in / numpy-out. ccdproc returns a
    fresh ``CCDData`` (no in-place mutation), so no functional refactor is needed.

    Parameters
    ----------
    frames
        Bias frames, each a 2D array of the same detector shape.
    method
        Combine method passed to ``ccdproc.combine`` (``"median"`` or
        ``"average"``).

    Returns
    -------
    numpy.ndarray
        The master bias, ``float64``, same shape as the inputs.

    Raises
    ------
    ValueError
        If no frames are supplied.
    """
    if not frames:
        raise ValueError("combine_master_bias requires at least one bias frame")
    ccds = [CCDData(frame.astype(np.float64), unit=u.adu) for frame in frames]
    master = combine(ccds, method=method)
    return np.asarray(master.data, dtype=np.float64)


def make_master_bias(level: float = 0.0) -> float | np.ndarray:
    """Build a master bias.

    Stub: return a constant pedestal ``level``. The real Phase 7 version will
    median-combine a stack of bias frames into a 2D master and ignore ``level``.

    Parameters
    ----------
    level
        Constant bias pedestal in counts.

    Returns
    -------
    float or numpy.ndarray
        The master bias (scalar pedestal in the stub).
    """
    return level


def make_master_dark(level: float = 0.0) -> float | np.ndarray:
    """Build a master dark.

    Stub: return a constant dark level. The real version will combine dark
    frames and scale by exposure time.

    Parameters
    ----------
    level
        Constant dark level in counts (already scaled to the science exposure).

    Returns
    -------
    float or numpy.ndarray
        The master dark (scalar level in the stub).
    """
    return level


def subtract_bias(frame: np.ndarray, master_bias: float | np.ndarray) -> np.ndarray:
    """Subtract the master bias from a frame, returning a new array.

    Parameters
    ----------
    frame
        2D science/flat frame, shape ``(nspec, nspatial)``.
    master_bias
        Scalar pedestal or 2D master (broadcast to ``frame``).

    Returns
    -------
    numpy.ndarray
        ``frame - master_bias`` as a new array; the input is not mutated.
    """
    return frame - master_bias


def subtract_dark(frame: np.ndarray, master_dark: float | np.ndarray) -> np.ndarray:
    """Subtract the master dark from a frame, returning a new array.

    Parameters
    ----------
    frame
        2D frame, shape ``(nspec, nspatial)``.
    master_dark
        Scalar level or 2D master (broadcast to ``frame``).

    Returns
    -------
    numpy.ndarray
        ``frame - master_dark`` as a new array; the input is not mutated.
    """
    return frame - master_dark
