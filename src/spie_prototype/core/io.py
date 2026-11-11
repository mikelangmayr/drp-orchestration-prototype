"""FITS frame I/O primitives.

These are the few ``core`` functions that are *fundamentally* about I/O, so
they are allowed to touch the filesystem per the layering rules. Everything
crossing the boundary is a standard type (``numpy.ndarray`` +
``astropy.io.fits.Header``, plain ``str`` paths) so the primitives stay
upstreamable and free of LRIS-2-internal objects.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from astropy.io import fits

# Recognized FITS extensions, each also matched with a trailing ``.gz`` so that
# KOA's gzipped raw frames (``LB.20020107.05505.fits.gz``) are discovered too.
_FITS_SUFFIXES = (".fits", ".fit", ".fts")


def _is_fits(name: str) -> bool:
    """Return True if ``name`` is a FITS frame, gzipped or not."""
    lowered = name.lower()
    if lowered.endswith(".gz"):
        lowered = lowered[: -len(".gz")]
    return lowered.endswith(_FITS_SUFFIXES)


def discover_fits(input_dir: str | Path, recursive: bool = False) -> list[str]:
    """Return the sorted FITS file paths under ``input_dir``.

    Matches ``.fits`` / ``.fit`` / ``.fts`` and their ``.gz`` variants, so KOA's
    gzipped raw downloads are found. KOA carts nest frames several directories
    deep, so set ``recursive=True`` for those.

    Parameters
    ----------
    input_dir
        Directory to scan.
    recursive
        If True, descend into subdirectories; otherwise scan only ``input_dir``.

    Returns
    -------
    list of str
        Absolute paths, sorted for deterministic fan-out ordering.
    """
    directory = Path(input_dir)
    entries = directory.rglob("*") if recursive else directory.iterdir()
    paths = [str(entry.resolve()) for entry in entries if entry.is_file() and _is_fits(entry.name)]
    return sorted(paths)


def load_flat_frame(path: str | Path, hdu: int = 0) -> tuple[np.ndarray, fits.Header]:
    """Load a FITS frame as float64 pixel data plus its header.

    Parameters
    ----------
    path
        Path to the FITS file.
    hdu
        Index of the HDU to read.

    Returns
    -------
    data
        2D pixel array, shape ``(nspec, nspatial)``, ``float64``.
    header
        A copy of the HDU header.

    Raises
    ------
    ValueError
        If the selected HDU contains no image data.
    """
    with fits.open(path) as hdul:
        image = hdul[hdu]
        if image.data is None:
            raise ValueError(f"HDU {hdu} of {path} contains no image data")
        data = image.data.astype(np.float64)
        header = image.header.copy()
    return data, header


def save_edges(left_edges: np.ndarray, right_edges: np.ndarray, output_path: str | Path) -> str:
    """Persist traced slit edges to a compressed ``.npz`` file.

    Parameters
    ----------
    left_edges, right_edges
        Edge position arrays, each shape ``(n_slits, nspec)``.
    output_path
        Destination path; parent directories are created as needed.

    Returns
    -------
    str
        The path written.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path, left_edges=left_edges, right_edges=right_edges)
    return str(path)
