"""Serial vs concurrent vs distributed timing across N frames (paper figure F11).

Times the same batch of N load+trace tasks under three Prefect task runners, with
identical scientific logic — only the runner changes (the paper's claim 3):

- **serial**            — ``ThreadPoolTaskRunner(max_workers=1)``: one at a time.
- **concurrent**        — ``ThreadPoolTaskRunner(max_workers=N)``: threads overlap
  (CPU-bound speedup is bounded by the GIL, and requires PypeIt to be thread-safe).
- **dask (processes)**  — ``DaskTaskRunner`` with N single-thread worker processes:
  true multi-core parallelism, and process isolation sidesteps GIL/thread-safety.

Each runner is timed independently and resiliently: if one runner errors (e.g.
PypeIt turning out not to be thread-safe under the thread runner), the others
still report. Tasks are uncached (``NO_CACHE``) so every run does real work; the
frames are cycled from ``--input`` so N independent trace workloads run.

Run with::

    python scripts/benchmark_parallel.py --input ../lris2-drp/data/lris2_flats --frames 3 --output figures/
"""
from __future__ import annotations

import argparse
import time
from itertools import cycle, islice
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from prefect import flow, task
from prefect.cache_policies import NO_CACHE
from prefect.task_runners import ThreadPoolTaskRunner

from spie_prototype.core.io import discover_fits, load_flat_frame
from spie_prototype.core.tracing import DEFAULT_SPECTROGRAPH, trace_slits


@task(name="Load+Trace (benchmark)", cache_policy=NO_CACHE, persist_result=False)
def _load_trace(path: str, spectrograph_name: str, fit_order: int, crop: int) -> int:
    """Load a frame (optionally cropped to crop x crop) and trace it; return slit count.

    ``crop`` controls per-task cost: concurrency only pays off once each task is
    long enough (~1 min) to amortize scheduling/setup overhead, so the benchmark
    exposes the frame size as a knob rather than hard-coding the full 4080^2.
    """
    import numpy as np

    data, _ = load_flat_frame(path)
    if crop:
        data = np.ascontiguousarray(data[:crop, :crop])
    left, _right, _ = trace_slits(data, spectrograph_name=spectrograph_name, fit_order=fit_order)
    return int(left.shape[0]) if left.size else 0


@flow(name="Parallel benchmark")
def _bench_flow(paths: list[str], spectrograph_name: str, fit_order: int, crop: int) -> list[int]:
    """Submit one load+trace task per frame and wait for all."""
    futures = [_load_trace.submit(p, spectrograph_name, fit_order, crop) for p in paths]
    return [f.result() for f in futures]


def _dask_runner(n_workers: int):
    """Build a DaskTaskRunner with N single-thread worker processes, or None if absent."""
    try:
        from prefect_dask import DaskTaskRunner
    except ImportError:
        return None
    # processes + one thread each -> genuine multi-core, GIL/thread-safety immaterial.
    return DaskTaskRunner(
        cluster_kwargs={"n_workers": n_workers, "threads_per_worker": 1, "processes": True}
    )


def _time_runner(runner, paths: list[str], spectrograph_name: str, fit_order: int, crop: int) -> float:
    clock = time.perf_counter()
    _bench_flow.with_options(task_runner=runner)(paths, spectrograph_name, fit_order, crop)
    return time.perf_counter() - clock


def _plot_f11(results: dict[str, float], serial: float, output_path: Path) -> None:
    labels = list(results)
    values = [results[k] for k in labels]
    colors = ["#ef5350", "#42a5f5", "#66bb6a"][: len(labels)]
    fig, ax = plt.subplots(figsize=(7.5, 5))
    bars = ax.bar(labels, values, color=colors)
    for label, bar, value in zip(labels, bars, values):
        speedup = f"\n{serial / value:.2f}x" if (value and label != "serial") else ""
        ax.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.0f}s{speedup}",
                ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("Wall-clock (s)")
    ax.set_title("Serial vs concurrent vs distributed — N trace tasks")
    fig.text(0.5, 0.01,
             "Same scientific logic; only the task runner changes. Threads are "
             "GIL-bound for CPU work; Dask worker\nprocesses give true multi-core "
             "parallelism (and sidestep thread-safety).",
             ha="center", va="bottom", fontsize=8, style="italic", color="#444444")
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main() -> None:
    """Time serial / concurrent / dask over N frames and write F11."""
    parser = argparse.ArgumentParser(description="Serial vs concurrent vs Dask benchmark (F11)")
    parser.add_argument("--input", required=True, help="Directory of FITS frames (cycled to N)")
    parser.add_argument("--frames", type=int, default=3, help="Number of trace tasks N")
    parser.add_argument("--crop", type=int, default=0, help="Crop frames to NxN (0 = full frame)")
    parser.add_argument("--output", default="figures", help="Figure output directory")
    parser.add_argument("--spectrograph", default=DEFAULT_SPECTROGRAPH, help="PypeIt spectrograph key")
    parser.add_argument("--fit-order", type=int, default=5, help="Trace polynomial fit order")
    args = parser.parse_args()

    available = discover_fits(args.input)
    if not available:
        raise SystemExit(f"No FITS frames found in {args.input}")
    paths = list(islice(cycle(available), args.frames))

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    runners = [
        ("serial", ThreadPoolTaskRunner(max_workers=1)),
        ("concurrent\n(threads)", ThreadPoolTaskRunner(max_workers=args.frames)),
        ("dask\n(processes)", _dask_runner(args.frames)),
    ]

    print(f"Timing {args.frames} trace tasks over {len(available)} distinct frames...")
    results: dict[str, float] = {}
    for label, runner in runners:
        if runner is None:
            print(f"{label!r}: SKIPPED (prefect-dask not installed)")
            continue
        try:
            elapsed = _time_runner(runner, paths, args.spectrograph, args.fit_order, args.crop)
            results[label] = elapsed
            print(f"{label.replace(chr(10), ' ')!r}: {elapsed:.1f}s")
        except Exception as exc:  # noqa: BLE001 — report the runner failure, keep the rest
            print(f"{label.replace(chr(10), ' ')!r}: FAILED ({type(exc).__name__}: {exc})")

    if "serial" in results:
        serial = results["serial"]
        for label, value in results.items():
            if label != "serial":
                print(f"speedup {label.replace(chr(10), ' ')}: {serial / value:.2f}x")
        _plot_f11(results, serial, out_dir / "serial_vs_parallel_timing.png")
        print(f"Wrote {out_dir / 'serial_vs_parallel_timing.png'} (F11)")


if __name__ == "__main__":
    main()
