"""Tracing primitive tests.

``get_slit_centers`` is pure and fast. ``trace_slits`` is a heavy PypeIt
integration, so it is exercised against a real flat and skipped when the sibling
data tree is unavailable (e.g. a checkout without the FITS frames).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from spie_prototype.core.io import discover_fits, load_flat_frame
from spie_prototype.core.tracing import get_slit_centers, trace_slits

# Test frames currently live in the sibling lris2-drp checkout, not in
# spie-prototype/ (see docs/plan.md open questions). parents[2] is the outer
# git/lris2-drp directory that holds both checkouts.
_FLATS_DIR = Path(__file__).resolve().parents[2] / "lris2-drp" / "data" / "lris2_flats"


def test_get_slit_centers_midpoint() -> None:
    left = np.array([[2.0, 4.0], [10.0, 12.0]])
    right = np.array([[6.0, 8.0], [14.0, 16.0]])

    centers = get_slit_centers(left, right)

    np.testing.assert_allclose(centers, [5.0, 13.0])


def test_get_slit_centers_empty() -> None:
    empty = np.empty((0, 8))
    assert get_slit_centers(empty, empty).size == 0


@pytest.mark.slow
@pytest.mark.skipif(not _FLATS_DIR.is_dir(), reason="sibling flat-field data not available")
def test_trace_slits_on_real_flat() -> None:
    flat_path = discover_fits(_FLATS_DIR)[0]
    data, _ = load_flat_frame(flat_path)

    left_edges, right_edges, raw_edges = trace_slits(data)

    assert left_edges.shape == right_edges.shape
    assert left_edges.shape[1] == data.shape[0]  # one column per spectral pixel
    assert left_edges.shape[0] > 0  # the flats are multi-slit; expect detections
    assert raw_edges is not None
