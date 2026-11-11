"""LRIS CAL DAG: build and cache master calibrations.

The calibration arm of the LRIS flow triad (ADR 0006). It builds the master
bias and master dark as independent — therefore parallel — cached tasks; the
Quicklook and Science DAGs consume its output as cache hits, across both flows
and re-runs.

Master bias has two builders (ADR 0008, polyglot composition): a **ccdproc**
(Astropy-ecosystem) median-combine of a real bias stack when ``bias_dir`` is
given, or a constant-pedestal stub otherwise. Either way the downstream subtract
and (Quicklook) PypeIt trace are unchanged — the DAG is primitive-source-agnostic.
Run standalone with::

    python -m spie_prototype.flows.lris.cal --bias-dir <dir of real bias frames>
"""
from __future__ import annotations

import argparse

from prefect import flow, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner

from spie_prototype.tasks import (
    combine_master_bias_task,
    discover_fits_task,
    load_flat_frame_task,
    make_master_bias_task,
    make_master_dark_task,
)


@flow(name="LRIS CAL", task_runner=ConcurrentTaskRunner())
def cal_flow(
    bias_level: float = 0.0,
    dark_level: float = 0.0,
    bias_dir: str | None = None,
    recursive: bool = False,
) -> dict[str, object]:
    """Build the master calibrations.

    When ``bias_dir`` is given, the master bias is a real ccdproc median-combine
    of that directory's frames (discover → load → combine); otherwise it is the
    constant-pedestal stub. The master dark is always the stub for now. The two
    arms are submitted together and run concurrently, and are cached, so they
    compute once and serve from cache to the Quicklook/Science DAGs and re-runs.

    Returns
    -------
    dict
        ``{"bias": <master bias>, "dark": <master dark>}``.
    """
    logger = get_run_logger()

    if bias_dir:
        bias_paths = discover_fits_task(bias_dir, recursive=recursive)
        loaded = [load_flat_frame_task.submit(path) for path in bias_paths]
        frames = [future.result()[0] for future in loaded]
        master_bias = combine_master_bias_task.submit(frames)  # ccdproc primitive
        logger.info(f"CAL: real master bias from {len(frames)} frames via ccdproc")
    else:
        master_bias = make_master_bias_task.submit(bias_level)  # stub pedestal

    master_dark = make_master_dark_task.submit(dark_level)
    masters = {"bias": master_bias.result(), "dark": master_dark.result()}
    logger.info(f"CAL masters ready (bias source: {'ccdproc' if bias_dir else 'stub'})")
    return masters


def main() -> None:
    """CLI entry point for ``python -m spie_prototype.flows.lris.cal``."""
    parser = argparse.ArgumentParser(description="Build LRIS master calibrations (CAL DAG)")
    parser.add_argument("--bias-level", type=float, default=0.0, help="Stub master-bias pedestal")
    parser.add_argument("--dark-level", type=float, default=0.0, help="Stub master-dark level")
    parser.add_argument("--bias-dir", default=None, help="Directory of real bias frames (ccdproc combine)")
    parser.add_argument("--recursive", action="store_true", help="Recurse into subdirectories")
    args = parser.parse_args()
    cal_flow(
        bias_level=args.bias_level, dark_level=args.dark_level,
        bias_dir=args.bias_dir, recursive=args.recursive,
    )


if __name__ == "__main__":
    main()
