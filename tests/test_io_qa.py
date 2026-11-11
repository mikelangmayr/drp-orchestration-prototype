"""Primitive tests for I/O and QA — run with no orchestration present."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from astropy.io import fits

from spie_prototype.core.io import discover_fits, load_flat_frame, save_edges
from spie_prototype.core.qa import generate_trace_qa_plot


def _write_fits(path: Path, data: np.ndarray) -> None:
    fits.PrimaryHDU(data=data).writeto(path, overwrite=True)


def test_discover_fits_sorted_and_filtered(tmp_path: Path) -> None:
    _write_fits(tmp_path / "b.fits", np.zeros((4, 4)))
    _write_fits(tmp_path / "a.fits", np.zeros((4, 4)))
    _write_fits(tmp_path / "c.fits.gz", np.zeros((4, 4)))  # gzipped KOA-style frame
    (tmp_path / "notes.txt").write_text("ignore me")

    found = discover_fits(tmp_path)

    assert [Path(p).name for p in found] == ["a.fits", "b.fits", "c.fits.gz"]


def test_discover_fits_recursive(tmp_path: Path) -> None:
    _write_fits(tmp_path / "top.fits", np.zeros((4, 4)))
    nested = tmp_path / "KOA" / "raw" / "cal"
    nested.mkdir(parents=True)
    _write_fits(nested / "deep.fits.gz", np.zeros((4, 4)))

    assert [Path(p).name for p in discover_fits(tmp_path)] == ["top.fits"]
    assert [Path(p).name for p in discover_fits(tmp_path, recursive=True)] == ["deep.fits.gz", "top.fits"]


def test_load_flat_frame_raises_on_corrupt_fits(tmp_path: Path) -> None:
    # The failure mode Flow C relies on: a corrupt FITS raises, which the
    # Quicklook flow isolates per-frame instead of halting the batch.
    corrupt = tmp_path / "corrupt.fits"
    corrupt.write_bytes(b"NOT A FITS FILE\n" * 64)
    with pytest.raises(Exception):
        load_flat_frame(corrupt)


def test_load_flat_frame_returns_float64_and_header(tmp_path: Path) -> None:
    path = tmp_path / "frame.fits"
    _write_fits(path, np.arange(16, dtype=np.int16).reshape(4, 4))

    data, header = load_flat_frame(path)

    assert data.dtype == np.float64
    assert data.shape == (4, 4)
    assert isinstance(header, fits.Header)


def test_save_edges_roundtrip(tmp_path: Path) -> None:
    left = np.array([[1.0, 1.1], [5.0, 5.1]])
    right = np.array([[2.0, 2.1], [6.0, 6.1]])

    written = save_edges(left, right, tmp_path / "nested" / "edges.npz")

    restored = np.load(written)
    np.testing.assert_allclose(restored["left_edges"], left)
    np.testing.assert_allclose(restored["right_edges"], right)


def test_generate_trace_qa_plot_writes_png(tmp_path: Path) -> None:
    data = np.random.default_rng(0).normal(size=(32, 32))
    left = np.full((1, 32), 8.0)
    right = np.full((1, 32), 24.0)

    written = generate_trace_qa_plot(data, left, right, tmp_path / "qa.png")

    assert Path(written).exists() and Path(written).stat().st_size > 0
