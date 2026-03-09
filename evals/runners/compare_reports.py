"""
Compare multiple RAGAS evaluation CSVs side-by-side.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
from rich.console import Console
from rich.table import Table

console = Console()

METRIC_COLUMNS = [
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
]


def load_report(path: str) -> tuple[str, pd.DataFrame]:
    return Path(path).stem, pd.read_csv(path)


def compare(paths: list[str]):
    reports = []

    for path in paths:
        try:
            reports.append(load_report(path))
        except Exception as e:
            console.print(f"[red]Failed to load {path}: {e}[/red]")

    if not reports:
        console.print("[red]No valid reports.[/red]")
        sys.exit(1)

    table = Table(title="RAGAS Metric Comparison")
    table.add_column("Metric", style="cyan")
    for label, _ in reports:
        table.add_column(label, justify="right", style="magenta")

    for column in METRIC_COLUMNS:
        scores = [
            f"{df[column].mean():.3f}" if column in df.columns else "N/A"
            for _, df in reports
        ]
        table.add_row(column.replace("_", " ").title(), *scores)

    console.print(table)

    if len(reports) > 1:
        baseline_label, baseline_df = reports[0]
        console.print(f"\n[bold]Delta vs baseline ({baseline_label})[/bold]")
        delta_table = Table()
        delta_table.add_column("Metric", style="cyan")
        for label, _ in reports[1:]:
            delta_table.add_column(f"{label} Δ", justify="right")

        for col in METRIC_COLUMNS:
            if col not in baseline_df.columns:
                continue
            base = baseline_df[col].mean()
            deltas = []
            for _, df in reports[1:]:
                if col in df.columns:
                    d = df[col].mean() - base
                    color = "green" if d >= 0 else "red"
                    deltas.append(f"[{color}]{d:+.3f}[/{color}]")
                else:
                    deltas.append("N/A")
            delta_table.add_row(col.replace("_", " ").title(), *deltas)
        console.print(delta_table)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csvs", nargs="+")
    args = parser.parse_args()
    compare(args.csvs)
