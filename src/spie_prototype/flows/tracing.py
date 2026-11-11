"""Slit-tracing flow: trace every FITS frame in a directory, concurrently.

The Phase 2 reduction slice and the spine the Flow A DAG grows from. Orchestration
is flat — every ``.submit()`` / ``.result()`` lives here, never inside a task — so
each step is visible on the Prefect dashboard. Run with::

    python -m spie_prototype.flows.tracing --input ../data/lris2_flats --output out/
"""
from __future__ import annotations

import argparse
from pathlib import Path

from prefect import flow, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner

from spie_prototype.core.tracing import DEFAULT_SPECTROGRAPH
from spie_prototype.tasks import (
    discover_fits_task,
    generate_trace_qa_plot_task,
    load_flat_frame_task,
    save_edges_task,
    trace_slits_task,
)


@flow(name="LRIS Slit Tracing", task_runner=ConcurrentTaskRunner())
def tracing_flow(
    input_dir: str,
    output_dir: str,
    spectrograph_name: str = DEFAULT_SPECTROGRAPH,
    fit_order: int = 5,
) -> None:
    """Trace slit edges in all FITS frames under ``input_dir``.

    Per-frame steps (load → trace → save + QA) carry data dependencies and run in
    order; across frames they run concurrently, which is the parallelism the
    paper's claim 3 rests on.
    """
    logger = get_run_logger()
    paths = discover_fits_task(input_dir)

    # Submit all loads, then all traces, before resolving any — so the CPU-bound
    # traces overlap across frames rather than serializing one frame at a time.
    load_futures = {path: load_flat_frame_task.submit(path) for path in paths}
    frames = {path: future.result()[0] for path, future in load_futures.items()}
    trace_futures = {
        path: trace_slits_task.submit(
            data, spectrograph_name=spectrograph_name, fit_order=fit_order
        )
        for path, data in frames.items()
    }

    output_futures = []
    for path, trace_future in trace_futures.items():
        left_edges, right_edges = trace_future.result()
        stem = Path(path).stem
        frame_dir = Path(output_dir) / stem
        output_futures.append(
            save_edges_task.submit(left_edges, right_edges, str(frame_dir / "slit_edges.npz"))
        )
        output_futures.append(
            generate_trace_qa_plot_task.submit(
                frames[path], left_edges, right_edges, str(frame_dir / "trace_qa.png"), title=stem
            )
        )

    for future in output_futures:
        future.result()
    logger.info(f"Traced {len(paths)} frames into {output_dir}")


def main() -> None:
    """CLI entry point for ``python -m spie_prototype.flows.tracing``."""
    parser = argparse.ArgumentParser(description="Trace slit edges in a directory of FITS frames")
    parser.add_argument("--input", required=True, help="Directory of input FITS frames")
    parser.add_argument("--output", required=True, help="Directory for outputs")
    parser.add_argument("--spectrograph", default=DEFAULT_SPECTROGRAPH, help="PypeIt spectrograph key")
    parser.add_argument("--fit-order", type=int, default=5, help="Trace polynomial fit order")
    args = parser.parse_args()
    tracing_flow(args.input, args.output, spectrograph_name=args.spectrograph, fit_order=args.fit_order)


if __name__ == "__main__":
    main()
