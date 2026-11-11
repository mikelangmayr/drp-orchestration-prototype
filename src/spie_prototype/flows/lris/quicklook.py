"""LRIS Quicklook DAG: fast, fixed-parameter reduction.

The real-time arm of the LRIS flow triad (ADR 0006). It runs the CAL DAG as a
subflow to obtain cached master calibrations, then per frame:
load → subtract bias → subtract dark → trace → save edges + QA. Frames fan out
concurrently. Fixed-boxcar 1D extraction joins here once an extraction primitive
lands. Run with::

    python -m spie_prototype.flows.lris.quicklook --input <dir> --output <dir>
"""
from __future__ import annotations

import argparse
from pathlib import Path

from prefect import flow, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner

from spie_prototype.core.tracing import DEFAULT_SPECTROGRAPH
from spie_prototype.flows.lris.cal import cal_flow
from spie_prototype.tasks import (
    bias_subtract_task,
    dark_subtract_task,
    discover_fits_task,
    generate_trace_qa_plot_task,
    load_flat_frame_task,
    save_edges_task,
    trace_slits_task,
)


@flow(name="LRIS Quicklook", task_runner=ConcurrentTaskRunner())
def quicklook_flow(
    input_dir: str,
    output_dir: str,
    bias_level: float = 0.0,
    dark_level: float = 0.0,
    spectrograph_name: str = DEFAULT_SPECTROGRAPH,
    fit_order: int = 5,
    recursive: bool = False,
) -> dict[str, object]:
    """Reduce every frame under ``input_dir`` through the Quicklook DAG.

    The CAL subflow's master-build tasks are cached, so on re-runs (e.g. after
    changing ``fit_order``) they serve from cache and only the per-frame chain
    re-executes — the selective-re-execution story.

    Per-frame failures are isolated: a frame that fails (e.g. a corrupt FITS)
    is logged with full context and skipped, and the rest of the batch completes.
    This is the real-time resilience requirement — one bad frame must not halt
    the night.

    Returns
    -------
    dict
        ``{"succeeded": [paths], "failed": {path: reason}}``.
    """
    logger = get_run_logger()
    masters = cal_flow(bias_level=bias_level, dark_level=dark_level)  # CAL DAG (cached)

    paths = discover_fits_task(input_dir, recursive=recursive)
    failed: dict[str, str] = {}

    # Submit all loads before resolving any. Isolate per-frame load failures so
    # one bad frame (broad catch here is a deliberate fault-isolation boundary)
    # cannot halt the batch; the failed task still shows Failed on the dashboard.
    load_futures = {path: load_flat_frame_task.submit(path) for path in paths}
    frames: dict[str, object] = {}
    for path, future in load_futures.items():
        try:
            frames[path] = future.result()[0]
        except Exception as exc:  # noqa: BLE001 — fault-isolation boundary
            failed[path] = f"load: {exc}"
            logger.error(f"Frame failed at load and was skipped: {path} ({exc})")

    # Reduce the survivors; fan out concurrently.
    debiased = {p: bias_subtract_task.submit(frames[p], masters["bias"]) for p in frames}
    calibrated = {p: dark_subtract_task.submit(debiased[p], masters["dark"]) for p in frames}
    trace_futures = {
        p: trace_slits_task.submit(calibrated[p], spectrograph_name=spectrograph_name, fit_order=fit_order)
        for p in frames
    }

    output_futures = []
    succeeded: list[str] = []
    for path in list(frames):
        try:
            left_edges, right_edges = trace_futures[path].result()
            calibrated_frame = calibrated[path].result()
        except Exception as exc:  # noqa: BLE001 — fault-isolation boundary
            failed[path] = f"reduce: {exc}"
            logger.error(f"Frame failed during reduction and was skipped: {path} ({exc})")
            continue
        frame_dir = Path(output_dir) / Path(path).stem
        output_futures.append(
            save_edges_task.submit(left_edges, right_edges, str(frame_dir / "slit_edges.npz"))
        )
        output_futures.append(
            generate_trace_qa_plot_task.submit(
                calibrated_frame, left_edges, right_edges,
                str(frame_dir / "trace_qa.png"), title=Path(path).stem,
            )
        )
        succeeded.append(path)

    for future in output_futures:
        try:
            future.result()
        except Exception as exc:  # noqa: BLE001 — fault-isolation boundary
            logger.error(f"Output write failed: {exc}")

    summary = f"Quicklook: {len(succeeded)} succeeded, {len(failed)} failed"
    logger.info(summary + (f"; failures: {failed}" if failed else ""))
    return {"succeeded": succeeded, "failed": failed}


def main() -> None:
    """CLI entry point for ``python -m spie_prototype.flows.lris.quicklook``."""
    parser = argparse.ArgumentParser(description="LRIS Quicklook reduction (Quicklook DAG)")
    parser.add_argument("--input", required=True, help="Directory of input FITS frames")
    parser.add_argument("--output", required=True, help="Directory for outputs")
    parser.add_argument("--bias-level", type=float, default=0.0, help="Stub master-bias pedestal")
    parser.add_argument("--dark-level", type=float, default=0.0, help="Stub master-dark level")
    parser.add_argument("--spectrograph", default=DEFAULT_SPECTROGRAPH, help="PypeIt spectrograph key")
    parser.add_argument("--fit-order", type=int, default=5, help="Trace polynomial fit order")
    parser.add_argument("--recursive", action="store_true", help="Recurse into subdirectories")
    args = parser.parse_args()
    quicklook_flow(
        args.input, args.output,
        bias_level=args.bias_level, dark_level=args.dark_level,
        spectrograph_name=args.spectrograph, fit_order=args.fit_order, recursive=args.recursive,
    )


if __name__ == "__main__":
    main()
