"""Calibration primitive tests — pure, no orchestration."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from spie_prototype.core.calibration import (
    combine_master_bias,
    make_master_bias,
    make_master_dark,
    subtract_bias,
    subtract_dark,
)
from spie_prototype.core.io import discover_fits, load_flat_frame

# Real LRIS-1 bias frames (lb0095–lb0101) for the polyglot ccdproc test.
_LRIS_BIAS_DIR = Path(__file__).resolve().parents[2] / "data" / "LRIS-Feige_34" / "calibration"


def test_combine_master_bias_median() -> None:
    # ccdproc median-combine: per-pixel median across the stack.
    frames = [np.full((4, 4), 100.0), np.full((4, 4), 102.0), np.full((4, 4), 110.0)]
    master = combine_master_bias(frames, method="median")
    assert master.shape == (4, 4)
    np.testing.assert_allclose(master, 102.0)  # median of {100, 102, 110}


def test_combine_master_bias_empty_raises() -> None:
    with pytest.raises(ValueError):
        combine_master_bias([])


@pytest.mark.skipif(not _LRIS_BIAS_DIR.is_dir(), reason="real LRIS-1 bias frames not available")
def test_combine_master_bias_on_real_lris_biases() -> None:
    bias_paths = [p for p in discover_fits(_LRIS_BIAS_DIR) if "lb00" in Path(p).name]
    frames = [load_flat_frame(p)[0] for p in bias_paths]
    assert len(frames) >= 5  # the 2002-01-07 suite has 7 biases

    master = combine_master_bias(frames)

    assert master.shape == frames[0].shape
    # A real master bias sits near the frames' typical level, not zero.
    assert 500.0 < float(np.median(master)) < 5000.0


def test_master_stubs_return_level() -> None:
    assert make_master_bias(100.0) == 100.0
    assert make_master_dark(5.0) == 5.0
    assert make_master_bias() == 0.0  # default pedestal


def test_subtract_bias_scalar_does_not_mutate_input() -> None:
    frame = np.full((4, 4), 50.0)
    original = frame.copy()

    corrected = subtract_bias(frame, 10.0)

    np.testing.assert_allclose(corrected, 40.0)
    np.testing.assert_allclose(frame, original)  # input untouched


def test_subtract_dark_broadcasts_2d_master() -> None:
    frame = np.array([[10.0, 20.0], [30.0, 40.0]])
    master_dark = np.array([[1.0, 2.0], [3.0, 4.0]])

    corrected = subtract_dark(frame, master_dark)

    np.testing.assert_allclose(corrected, [[9.0, 18.0], [27.0, 36.0]])


def test_zero_master_is_passthrough() -> None:
    frame = np.arange(9.0).reshape(3, 3)
    np.testing.assert_allclose(subtract_bias(frame, 0.0), frame)
    np.testing.assert_allclose(subtract_dark(frame, 0.0), frame)
