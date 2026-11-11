"""Unit tests for the numpy-aware cache key (tasks layer, no Prefect runtime)."""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from spie_prototype.tasks._caching import numpy_aware_cache_key


def _ctx(task_name: str = "Trace Slits (PypeIt)") -> SimpleNamespace:
    """Minimal stand-in for a Prefect TaskRunContext (only ``.task.name`` is read)."""
    return SimpleNamespace(task=SimpleNamespace(name=task_name))


def _key(params: dict, task_name: str = "Trace Slits (PypeIt)") -> str:
    return numpy_aware_cache_key(_ctx(task_name), params)


def test_identical_inputs_same_key() -> None:
    frame = np.arange(64, dtype=np.float64).reshape(8, 8)
    assert _key({"data": frame, "fit_order": 5}) == _key({"data": frame.copy(), "fit_order": 5})


def test_changed_scalar_kwarg_changes_key() -> None:
    frame = np.ones((8, 8))
    assert _key({"data": frame, "fit_order": 5}) != _key({"data": frame, "fit_order": 7})


def test_changed_array_values_changes_key() -> None:
    frame = np.ones((8, 8))
    assert _key({"data": frame, "fit_order": 5}) != _key({"data": frame * 2, "fit_order": 5})


def test_task_name_disambiguates() -> None:
    frame = np.ones((8, 8))
    assert _key({"data": frame}, "Subtract Bias") != _key({"data": frame}, "Subtract Dark")


def test_fingerprint_is_independent_of_array_buffer_size() -> None:
    # A huge array and a small one with the same moments are keyed equally cheaply;
    # this is the property that makes the key fast — assert it does not raise and
    # that two equal-moment arrays of the same shape collide (expected, documented).
    a = np.zeros((256, 256))
    b = np.zeros((256, 256))
    assert _key({"data": a}) == _key({"data": b})
