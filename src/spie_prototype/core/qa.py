"""Quality-assurance plotting primitives.

Rendering a QA figure is an I/O effect (it writes a PNG), so these primitives
are the figure-producing exception to the no-side-effects rule. They take plain
numpy arrays and a path; they know nothing about Prefect.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend: these run headless in tasks
import matplotlib.pyplot as plt
import numpy as np

# Slit edges drawn near these display percentiles render well across frames.
_DISPLAY_PERCENTILES = (1.0, 99.0)
_LEGEND_SLIT_LIMIT = 10


def generate_trace_qa_plot(
    data: np.ndarray,
    left_edges: np.ndarray,
    right_edges: np.ndarray,
    output_path: str | Path,
    title: str = "Slit Trace QA",
    vmin: float | None = None,
    vmax: float | None = None,
) -> str:
    """Render traced slit edges overlaid on the flat image.

    Parameters
    ----------
    data
        2D flat-field image, shape ``(nspec, nspatial)``.
    left_edges, right_edges
        Edge arrays, each shape ``(n_slits, nspec)``.
    output_path
        Destination PNG path; parent directories are created as needed.
    title
        Plot title; the detected slit count is appended.
    vmin, vmax
        Display limits; default to the 1st/99th percentile of ``data``.

    Returns
    -------
    str
        The path written.

    Raises
    ------
    ValueError
        If ``data`` is not a 2D array.
    """
    if data is None or not hasattr(data, "shape") or data.ndim != 2:
        raise ValueError(f"Invalid data shape for QA plot: {getattr(data, 'shape', None)}")

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    low, high = _DISPLAY_PERCENTILES
    if vmin is None:
        vmin = float(np.percentile(data, low))
    if vmax is None:
        vmax = float(np.percentile(data, high))

    fig, ax = plt.subplots(figsize=(12, 8))
    image = ax.imshow(data, cmap="gray", aspect="auto", origin="lower", vmin=vmin, vmax=vmax)
    fig.colorbar(image, ax=ax, label="Counts")

    n_slits = left_edges.shape[0] if left_edges.size > 0 else 0
    spectral_coords = np.arange(data.shape[0])
    colors = plt.cm.tab10(np.linspace(0, 1, max(n_slits, 1)))

    for i in range(n_slits):
        color = colors[i % len(colors)]
        label = f"Slit {i + 1}" if i < _LEGEND_SLIT_LIMIT else None
        ax.plot(left_edges[i], spectral_coords, color=color, linewidth=1.5, label=label)
        ax.plot(right_edges[i], spectral_coords, color=color, linewidth=1.5, linestyle="--")

    ax.set_xlabel("Spatial (pixels)")
    ax.set_ylabel("Spectral (pixels)")
    ax.set_title(f"{title} — {n_slits} slits detected")
    if 0 < n_slits <= _LEGEND_SLIT_LIMIT:
        ax.legend(loc="upper right", fontsize=8)

    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return str(path)
