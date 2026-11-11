"""Slit-edge tracing primitive, backed by PypeIt's ``EdgeTraceSet``.

This is the flagship "polyglot primitive": the science is borrowed from PypeIt
(BSD-3, imported not vendored) and wrapped behind a plain numpy-in / numpy-out
signature. The orchestration layer never sees PypeIt — it sees arrays. A likely
upstream contribution is a ``trace_from_array`` entry point so callers need not
construct a ``TraceImage`` by hand; that adapter lives here for now.
"""
from __future__ import annotations

import warnings
from functools import lru_cache

import numpy as np
import pypeit
from pypeit.edgetrace import EdgeTraceSet
from pypeit.images.buildimage import TraceImage
from pypeit.par.pypeitpar import EdgeTracePar
from pypeit.spectrographs.util import load_spectrograph

# Pinned in pyproject.toml. The API surface used here (EdgeTraceSet,
# EdgeTracePar, TraceImage) is version-sensitive, so flag any mismatch rather
# than fail silently — warn instead of assert so notebook/CI use across a
# compatible patch release is not blocked outright.
_EXPECTED_PYPEIT = "1.18.1"
if pypeit.__version__ != _EXPECTED_PYPEIT:
    warnings.warn(
        f"pypeit {pypeit.__version__} differs from the pinned {_EXPECTED_PYPEIT}; "
        "slit-tracing behavior is only verified against the pinned version",
        RuntimeWarning,
        stacklevel=2,
    )

# LRIS-1 spectrograph definitions stand in for LRIS-2 until the latter ships in
# PypeIt. keck_lris_red / keck_lris_blue are the supported proxies.
DEFAULT_SPECTROGRAPH = "keck_lris_red"


@lru_cache(maxsize=4)
def _spectrograph(name: str):
    """Return a cached PypeIt spectrograph; loading is slow and stateless."""
    return load_spectrograph(name)


def trace_slits(
    data: np.ndarray,
    spectrograph_name: str = DEFAULT_SPECTROGRAPH,
    fwhm_uniform: float = 3.0,
    niter_uniform: int = 9,
    det_min_spec_length: float = 0.3,
    follow_span: int = 20,
    fit_order: int = 5,
) -> tuple[np.ndarray, np.ndarray, object | None]:
    """Trace slit edges in a flat-field frame.

    Parameters
    ----------
    data
        2D image, shape ``(nspec, nspatial)``, float64.
    spectrograph_name
        PypeIt spectrograph key. ``keck_lris_red`` / ``keck_lris_blue`` proxy
        for LRIS-2 during evaluation.
    fwhm_uniform, niter_uniform, det_min_spec_length, follow_span, fit_order
        ``EdgeTracePar`` knobs forwarded to PypeIt's edge detection and fit.

    Returns
    -------
    left_edges
        Left edge positions, shape ``(n_slits, nspec)``. Empty if none found.
    right_edges
        Right edge positions, shape ``(n_slits, nspec)``.
    raw_edges
        The raw ``EdgeTraceSet`` for advanced use (saving, QA); ``None`` only if
        construction yields no fit.
    """
    spectrograph = _spectrograph(spectrograph_name)

    edge_par = EdgeTracePar()
    edge_par["fwhm_uniform"] = fwhm_uniform
    edge_par["niter_uniform"] = niter_uniform
    edge_par["det_min_spec_length"] = det_min_spec_length
    edge_par["follow_span"] = follow_span
    edge_par["fit_order"] = fit_order

    trace_image = TraceImage(data.astype(np.float64))

    # auto=True runs the full PypeIt pipeline: detection, PCA, edge sync, fit.
    edges = EdgeTraceSet(trace_image, spectrograph=spectrograph, par=edge_par, auto=True)

    nspec = data.shape[0]
    if edges.edge_fit is None or edges.edge_fit.size == 0:
        empty = np.empty((0, nspec))
        return empty, empty, edges

    # PypeIt encodes left edges with negative trace ids, right with positive.
    edge_positions = edges.edge_fit  # shape (nspec, n_trace)
    left_edges = edge_positions[:, edges.traceid < 0].T
    right_edges = edge_positions[:, edges.traceid > 0].T
    return left_edges, right_edges, edges


def get_slit_centers(left_edges: np.ndarray, right_edges: np.ndarray) -> np.ndarray:
    """Return the median spatial center of each slit.

    A plain function, not a task: it runs in microseconds and has nothing worth
    inspecting on the dashboard (see ``docs/architecture.md`` §"Task granularity").

    Parameters
    ----------
    left_edges, right_edges
        Edge arrays from :func:`trace_slits`, each shape ``(n_slits, nspec)``.

    Returns
    -------
    numpy.ndarray
        One center per slit (median across the spectral direction). Empty if no
        edges were supplied.
    """
    if left_edges.size == 0 or right_edges.size == 0:
        return np.empty(0)
    return (np.median(left_edges, axis=1) + np.median(right_edges, axis=1)) / 2.0
