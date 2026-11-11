"""Flow C — graceful failure across a batch (paper figure F10).

Runs the LRIS Quicklook DAG over a batch of good frames plus one deliberately
corrupt FITS, and shows the resilience property: the bad frame fails with full
context (visible as a Failed task on the dashboard) while every other frame
completes. The script-driven counterfactual — the whole batch halts or silently
produces wrong output — is the contrast the paper draws.

The good frames are symlinked (not copied) from ``--input`` and their traces are
served from cache when warm, so the demo is fast. Run with::

    python scripts/demo_graceful_failure.py \
        --input ../lris2-drp/data/lris2_flats --output out/

F10 (the dashboard view of the batch, one frame red) is a live-UI capture; see
``scripts/capture_dashboard.py``.
"""
from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from spie_prototype.core.io import discover_fits
from spie_prototype.flows.lris.quicklook import quicklook_flow

_CORRUPT_BYTES = b"THIS IS NOT A VALID FITS FILE\n" * 64


def _build_batch(good_dir: str) -> Path:
    """Assemble a temp input dir: symlinks to the good frames + one corrupt FITS."""
    batch = Path(tempfile.mkdtemp(prefix="spie-flowc-"))
    for source in discover_fits(good_dir):
        (batch / Path(source).name).symlink_to(source)
    (batch / "corrupt_frame.fits").write_bytes(_CORRUPT_BYTES)
    return batch


def main() -> None:
    """Run the Quicklook DAG over a batch with one corrupt frame and report."""
    parser = argparse.ArgumentParser(description="Graceful-failure demo (Flow C, figure F10)")
    parser.add_argument("--input", required=True, help="Directory of good FITS frames")
    parser.add_argument("--output", default=None, help="Output directory (default: temp)")
    args = parser.parse_args()

    batch = _build_batch(args.input)
    output = args.output or tempfile.mkdtemp(prefix="spie-flowc-out-")
    frames = discover_fits(batch)
    print(f"Batch of {len(frames)} frames ({len(frames) - 1} good + 1 corrupt) in {batch}")

    result = quicklook_flow(str(batch), output)

    print("\n=== Flow C result ===")
    print(f"succeeded ({len(result['succeeded'])}):")
    for path in result["succeeded"]:
        print(f"    {Path(path).name}")
    print(f"failed ({len(result['failed'])}):")
    for path, reason in result["failed"].items():
        print(f"    {Path(path).name}: {reason}")

    ok = len(result["failed"]) == 1 and len(result["succeeded"]) == len(frames) - 1
    print(f"\nGraceful failure demonstrated: {ok} "
          "(1 frame failed with context, the rest completed)")
    print("F10 (dashboard view) — capture with scripts/capture_dashboard.py against a live server.")


if __name__ == "__main__":
    main()
