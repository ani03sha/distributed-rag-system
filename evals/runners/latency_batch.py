"""
Latency benchmark: p50/p95/p99 split by cache hit vs miss.
"""

import argparse
import csv
import statistics
import sys
import time
from datetime import datetime, UTC
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from rich.console import Console
from rich.table import Table

from runners.auth_client import AutoRefreshAuth

console = Console()

QUERY_URL = "http://localhost:8001/v1/query"

BENCH_QUESTIONS = [
    "What is the CAP theorem?",
    "What is eventual consistency?",
    "What is consistent hashing?",
    "What is the Raft consensus algorithm?",
    "What is the gossip protocol?",
]


def timed_query(client: httpx.Client, question: str) -> tuple[float, bool]:
    start = time.perf_counter()
    response = client.post(
        QUERY_URL,
        json={"text": question, "top_k": 5, "stream": False},
        timeout=300.0,
    )

    elapsed = time.perf_counter() - start
    response.raise_for_status()
    return elapsed, response.json().get("cached", False)


def percentile(data: list[float], p: int) -> float:
    if not data:
        return 0.0

    data_sorted = sorted(data)
    return data_sorted[min(int(len(data_sorted) * p / 100), len(data_sorted) - 1)]


def run(api_key: str, rounds: int, output: str) -> None:
    Path(output).parent.mkdir(parents=True, exist_ok=True)

    auth = AutoRefreshAuth(api_key=api_key, base_url="http://localhost:8001")
    client = httpx.Client(auth=auth, timeout=300.0)

    miss_times, hit_times, rows = [], [], []
    total = len(BENCH_QUESTIONS) * rounds
    done = 0

    for question in BENCH_QUESTIONS:
        for r in range(rounds):
            done += 1
            console.print(f"[{done}/{total}] round={r+1} Q: {question[:60]}")
            try:
                elapsed, cached = timed_query(client, question)
                (hit_times if cached else miss_times).append(elapsed)
                status = "[green]HIT[/green]" if cached else "[yellow]MISS[/yellow]"
                console.print(f"  {status}  {elapsed:.2f}s")
                rows.append(
                    {
                        "question": question,
                        "round": r + 1,
                        "elapsed_s": round(elapsed, 3),
                        "cached": cached,
                    }
                )
            except Exception as e:
                console.print(f"  [red]ERROR: {e}[/red]")

    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["question", "round", "elapsed_s", "cached"]
        )
        writer.writeheader()
        writer.writerows(rows)

    console.print(f"\n[green]Raw data saved to {output}[/green]")

    table = Table(title="Latency Benchmark Summary")
    table.add_column("Segment", style="cyan")
    table.add_column("n", justify="right")
    table.add_column("p50 (s)", justify="right", style="magenta")
    table.add_column("p95 (s)", justify="right", style="magenta")
    table.add_column("p99 (s)", justify="right", style="magenta")
    table.add_column("mean (s)", justify="right")

    for label, data in [("Cache MISS", miss_times), ("Cache HIT", hit_times)]:
        if data:
            table.add_row(
                label,
                str(len(data)),
                f"{percentile(data, 50):.2f}",
                f"{percentile(data, 95):.2f}",
                f"{percentile(data, 99):.2f}",
                f"{statistics.mean(data):.2f}",
            )
        else:
            table.add_row(label, "0", "-", "-", "-", "-")

    console.print(table)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument(
        "--output",
        default=f"results/latency_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.csv",
    )
    args = parser.parse_args()
    run(args.api_key, args.rounds, args.output)
