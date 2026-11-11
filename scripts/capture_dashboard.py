"""Capture a Prefect dashboard screenshot for a flow run (paper figure F4).

The dashboard is a live web UI, so a real screenshot needs a running Prefect
server *and* a headless browser. Playwright is the browser driver, but it is an
optional, un-pinned dependency here (installing it is a deliberate choice, not a
default). This script therefore:

1. Resolves the dashboard URL for a flow run (given ``--flow-run-id`` or the most
   recent run), using only the Prefect client that ships with the project.
2. Screenshots it with Playwright if that package is importable.
3. Otherwise prints the URL and the one-time install command, so the figure can
   still be captured manually.

Usage::

    prefect server start                       # in another terminal
    python -m spie_prototype.flows.reduce --input ... --output ...
    python scripts/capture_dashboard.py --output figures/
    # or target a specific run:
    python scripts/capture_dashboard.py --flow-run-id <uuid> --output figures/
"""
from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from prefect.client.orchestration import get_client
from prefect.client.schemas.filters import FlowFilter, FlowFilterName
from prefect.client.schemas.sorting import FlowRunSort


async def _resolve_flow_run_id(flow_run_id: str | None, flow_name: str | None) -> str:
    """Return the requested flow-run id, or the most recent run (of ``flow_name`` if given)."""
    if flow_run_id:
        return flow_run_id
    flow_filter = FlowFilter(name=FlowFilterName(any_=[flow_name])) if flow_name else None
    async with get_client() as client:
        runs = await client.read_flow_runs(
            flow_filter=flow_filter, sort=FlowRunSort.START_TIME_DESC, limit=1
        )
    if not runs:
        raise SystemExit(f"No flow runs found (flow_name={flow_name}) — run a flow first.")
    return str(runs[0].id)


def _dashboard_url(flow_run_id: str) -> str:
    """Build the UI URL for a flow run from the configured Prefect UI base."""
    base = os.environ.get("PREFECT_UI_URL", "http://localhost:4200").rstrip("/")
    return f"{base}/runs/flow-run/{flow_run_id}"


def _screenshot(url: str, output_path: Path, render_wait_ms: int = 6000) -> bool:
    """Screenshot ``url`` to ``output_path`` with Playwright; return success.

    The Prefect UI is a polling single-page app, so ``networkidle`` may never
    fire; we wait for the document to load, then a fixed interval for the run
    graph/timeline to render. Playwright is imported lazily so the script stays
    useful (URL resolution) even when it is not installed.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1680, "height": 1050})
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(render_wait_ms)
        # Dismiss the "Join the Prefect Community" popup if it appears.
        for label in ("Skip", "Close", "No thanks"):
            try:
                page.get_by_role("button", name=label).click(timeout=1500)
                page.wait_for_timeout(1000)
                break
            except Exception:
                continue
        page.wait_for_timeout(1500)
        page.screenshot(path=str(output_path), full_page=True)
        browser.close()
    return True


def main() -> None:
    """Resolve a flow run's dashboard URL and screenshot it if possible."""
    parser = argparse.ArgumentParser(description="Capture a Prefect dashboard screenshot (figure F4)")
    parser.add_argument("--flow-run-id", default=None, help="Flow run UUID (default: most recent run)")
    parser.add_argument("--flow-name", default=None, help="Pick most recent run of this flow (e.g. 'LRIS Quicklook')")
    parser.add_argument("--output", default="figures", help="Output directory")
    parser.add_argument("--name", default="flow_a_dashboard.png", help="Output PNG filename")
    args = parser.parse_args()

    flow_run_id = asyncio.run(_resolve_flow_run_id(args.flow_run_id, args.flow_name))
    url = _dashboard_url(flow_run_id)

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / args.name

    if _screenshot(url, output_path):
        print(f"Captured dashboard for run {flow_run_id} -> {output_path}")
    else:
        print(
            "Playwright is not installed, so no screenshot was taken.\n"
            f"  Dashboard URL: {url}\n"
            "  To enable automated capture:\n"
            "    pip install playwright && playwright install chromium\n"
            "  Or open the URL above and screenshot it manually."
        )


if __name__ == "__main__":
    main()
