"""Render the Flow A DAG as paper figure F7.

Produces two artifacts in the output directory:

- ``flow_a_dag.mmd`` — Mermaid source (editable, renders on GitHub / in docs).
- ``flow_a_dag.png`` — a matplotlib-drawn diagram (immediate figure, no extra
  system dependencies; Prefect's own ``flow.visualize`` needs the Graphviz
  ``dot`` binary, which is not assumed here).

The DAG structure is encoded once below and shared by both renderers, so the
figure cannot drift from a hand-edited Mermaid file. Run with::

    python scripts/render_dag.py --output figures/
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


@dataclass(frozen=True)
class Node:
    """A DAG node with a display label and a 2D layout position."""

    key: str
    label: str
    x: float
    y: float


# Flow A nodes laid out left-to-right. The two master-build arms sit at the
# left and feed the per-frame chain; Save and QA fan out from Trace.
_NODES: tuple[Node, ...] = (
    Node("DISC", "Discover\nFITS Frames", 0.0, 4.2),
    Node("MB", "Build\nMaster Bias", 0.0, 2.6),
    Node("MD", "Build\nMaster Dark", 0.0, 1.0),
    Node("LOAD", "Load\nFlat Frame", 1.8, 4.2),
    Node("SB", "Subtract\nBias", 3.6, 3.4),
    Node("SD", "Subtract\nDark", 5.4, 2.2),
    Node("TR", "Trace Slits\n(PypeIt)", 7.2, 2.2),
    Node("SAVE", "Save\nSlit Edges", 9.0, 3.0),
    Node("QA", "Trace\nQA Plot", 9.0, 1.4),
)

# (source, target) edges. The master arms join the per-frame chain at the
# corresponding subtract steps.
_EDGES: tuple[tuple[str, str], ...] = (
    ("DISC", "LOAD"),
    ("LOAD", "SB"),
    ("MB", "SB"),
    ("SB", "SD"),
    ("MD", "SD"),
    ("SD", "TR"),
    ("TR", "SAVE"),
    ("TR", "QA"),
)

_ARM_NODES = frozenset({"MB", "MD"})
_OUTPUT_NODES = frozenset({"SAVE", "QA"})


def _write_mermaid(path: Path) -> None:
    lines = [
        "flowchart LR",
        "  DISC[Discover FITS Frames]",
        "  MB[Build Master Bias]",
        "  MD[Build Master Dark]",
        '  subgraph frame["per frame x N (concurrent)"]',
        "    LOAD[Load Flat Frame]",
        "    SB[Subtract Bias]",
        "    SD[Subtract Dark]",
        "    TR[Trace Slits PypeIt]",
        "    SAVE[Save Slit Edges]",
        "    QA[Trace QA Plot]",
        "  end",
    ]
    lines += [f"  {src} --> {dst}" for src, dst in _EDGES]
    path.write_text("\n".join(lines) + "\n")


def _node_color(key: str) -> str:
    if key in _ARM_NODES:
        return "#ffe0b2"  # calibration arms
    if key in _OUTPUT_NODES:
        return "#c8e6c9"  # outputs
    return "#bbdefb"  # pipeline steps


def _render_png(path: Path) -> None:
    positions = {node.key: (node.x, node.y) for node in _NODES}
    fig, ax = plt.subplots(figsize=(12, 5))

    for src, dst in _EDGES:
        x0, y0 = positions[src]
        x1, y1 = positions[dst]
        ax.add_patch(
            FancyArrowPatch(
                (x0 + 0.55, y0), (x1 - 0.55, y1),
                arrowstyle="-|>", mutation_scale=14, color="#555555",
                shrinkA=0, shrinkB=0, linewidth=1.3,
            )
        )

    for node in _NODES:
        ax.add_patch(
            FancyBboxPatch(
                (node.x - 0.6, node.y - 0.32), 1.2, 0.64,
                boxstyle="round,pad=0.02,rounding_size=0.12",
                facecolor=_node_color(node.key), edgecolor="#37474f", linewidth=1.2,
            )
        )
        ax.text(node.x, node.y, node.label, ha="center", va="center", fontsize=8.5)

    ax.text(5.4, 0.1, "per-frame chain repeats x N frames (concurrent)",
            ha="center", va="center", fontsize=8, style="italic", color="#555555")
    ax.set_title("Flow A — LRIS Reduction DAG", fontsize=12)
    ax.set_xlim(-1.0, 10.0)
    ax.set_ylim(-0.2, 5.0)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    """Write the Mermaid source and PNG for the Flow A DAG."""
    parser = argparse.ArgumentParser(description="Render the Flow A DAG (figure F7)")
    parser.add_argument("--output", default="figures", help="Output directory")
    args = parser.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_mermaid(out_dir / "flow_a_dag.mmd")
    _render_png(out_dir / "flow_a_dag.png")
    print(f"Wrote {out_dir / 'flow_a_dag.mmd'} and {out_dir / 'flow_a_dag.png'}")


if __name__ == "__main__":
    main()
