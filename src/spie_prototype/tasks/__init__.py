"""Thin Prefect task wrappers around ``core`` primitives.

A wrapper adds logging, caching, retries, and a human-readable dashboard name —
and nothing of substance. It never reimplements logic. See
``docs/architecture.md`` §"The task wrapping pattern".

Tasks are re-exported here so flows can import the whole vocabulary from one
place (``from spie_prototype.tasks import ...``).
"""
from spie_prototype.tasks.calibration import (
    bias_subtract_task,
    combine_master_bias_task,
    dark_subtract_task,
    make_master_bias_task,
    make_master_dark_task,
)
from spie_prototype.tasks.io import (
    discover_fits_task,
    load_flat_frame_task,
    save_edges_task,
)
from spie_prototype.tasks.qa import generate_trace_qa_plot_task
from spie_prototype.tasks.tracing import trace_slits_task

__all__ = [
    "make_master_bias_task",
    "make_master_dark_task",
    "combine_master_bias_task",
    "bias_subtract_task",
    "dark_subtract_task",
    "discover_fits_task",
    "load_flat_frame_task",
    "save_edges_task",
    "generate_trace_qa_plot_task",
    "trace_slits_task",
]
