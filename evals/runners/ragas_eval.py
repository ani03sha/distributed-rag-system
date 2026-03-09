"""
Two-phase RAGAS evaluation.

Phase 1 — fetch answers from the running query service:
    uv run python runners/ragas_eval.py fetch \\
        --api-key "dev-key-1" \\
        --golden datasets/candidates.json \\
        --answers datasets/answers_cache.json

Phase 2 — score with a local judge LLM (query service can be stopped):
    JUDGE_MODEL=llama3.1:8b uv run python runners/ragas_eval.py score \\
        --answers datasets/answers_cache.json \\
        --output results/ragas_v1.csv
"""

import argparse
import asyncio
import csv
import json
import os
import sys
from datetime import datetime, UTC
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import warnings
import httpx
import ollama as ollama_pkg
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_ollama import OllamaEmbeddings
from ragas.dataset_schema import SingleTurnSample
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper


class OllamaDirectLLM(BaseChatModel):
    """Thin LangChain wrapper around the ollama Python package.

    LangChain's ChatOllama uses httpx async internals that conflict with
    asyncio.run() and cause the Ollama runner to be killed. The ollama package
    uses a plain synchronous requests-based client which works reliably.
    """

    model_name: str

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        ollama_messages = [
            {"role": "user" if m.type == "human" else m.type, "content": m.content}
            for m in messages
        ]
        resp = ollama_pkg.chat(model=self.model_name, messages=ollama_messages)
        content = resp["message"]["content"]
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        # Delegate to sync — keeps everything on one thread, avoids event loop issues
        return self._generate(messages, stop=stop, **kwargs)

    @property
    def _llm_type(self) -> str:
        return "ollama-direct"

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from ragas.metrics import (
        Faithfulness,
        AnswerRelevancy,
        LLMContextPrecisionWithReference,
        LLMContextRecall,
    )

from rich.console import Console
from rich.table import Table

from runners.auth_client import AutoRefreshAuth

console = Console()

QUERY_URL = "http://localhost:8001/v1/query"
OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "qwen2.5:14b")


# ---------------------------------------------------------------------------
# Phase 1: fetch
# ---------------------------------------------------------------------------

def fetch(api_key: str, golden_path: str, answers_path: str) -> None:
    """Query the running RAG service and save answers to a local cache file."""
    with open(golden_path) as f:
        data = json.load(f)
    golden = [row for row in data if row.get("review_status") == "approved"]
    console.print(f"[bold]Golden set:[/bold] {len(data)} total, {len(golden)} approved")

    if not golden:
        console.print("[red]No approved entries.[/red]")
        return

    # Resume: skip questions already fetched
    answers_file = Path(answers_path)
    if answers_file.exists():
        with open(answers_file) as f:
            existing = {r["question"]: r for r in json.load(f)}
    else:
        existing = {}

    auth = AutoRefreshAuth(api_key=api_key, base_url="http://localhost:8001")
    client = httpx.Client(auth=auth, timeout=180.0)
    results = dict(existing)

    for i, row in enumerate(golden, 1):
        q = row["question"]
        if q in results:
            console.print(f" [{i}/{len(golden)}] (cached) {q[:70]}")
            continue
        console.print(f" [{i}/{len(golden)}] {q[:70]}")
        try:
            resp = client.post(QUERY_URL, json={"text": q, "top_k": 5, "stream": False})
            resp.raise_for_status()
            data_resp = resp.json()
            results[q] = {
                "question": q,
                "ground_truth": row["ground_truth"],
                "answer": data_resp["answer"],
                "contexts": [s["chunk_text"] for s in data_resp.get("sources", [])],
            }
            answers_file.parent.mkdir(parents=True, exist_ok=True)
            with open(answers_file, "w") as f:
                json.dump(list(results.values()), f, indent=2)
            console.print(f"  -> saved ({len(results)} total)")
        except Exception as e:
            console.print(f"  [red]ERROR: {e}[/red]")

    console.print(f"\n[green]Answers saved to {answers_path}[/green]")
    console.print("Now stop the query service and run: ragas_eval.py score ...")


# ---------------------------------------------------------------------------
# Phase 2: score
# ---------------------------------------------------------------------------

def score(answers_path: str, output: str) -> None:
    """Run RAGAS metrics on pre-fetched answers. Query service not needed."""
    with open(answers_path) as f:
        rows = json.load(f)

    if not rows:
        console.print("[red]No answers found in cache.[/red]")
        return

    console.print(f"\n[bold]Running RAGAS with judge: {JUDGE_MODEL}[/bold]")
    console.print(f"[bold]{len(rows)} samples — fully sequential[/bold]")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        judge_llm = LangchainLLMWrapper(OllamaDirectLLM(model_name=JUDGE_MODEL))
        judge_embeddings = LangchainEmbeddingsWrapper(
            OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_BASE)
        )
        faithfulness_m = Faithfulness(llm=judge_llm)
        relevancy_m = AnswerRelevancy(llm=judge_llm, embeddings=judge_embeddings)
        precision_m = LLMContextPrecisionWithReference(llm=judge_llm)
        recall_m = LLMContextRecall(llm=judge_llm)

    # Truncate contexts so prompts stay within num_ctx
    def _trunc(contexts: list[str], max_words: int = 200) -> list[str]:
        return [" ".join(c.split()[:max_words]) for c in contexts]

    records = []
    total = len(rows)
    for i, row in enumerate(rows, 1):
        q = row["question"]
        a = row["answer"]
        ctxs = _trunc(row["contexts"])
        ref = row["ground_truth"]
        console.print(f"\n[{i}/{total}] {q[:70]}")

        sample = SingleTurnSample(
            user_input=q,
            response=a,
            retrieved_contexts=ctxs,
            reference=ref,
        )
        rec = {"question": q, "answer": a, "ground_truth": ref}
        for label, metric in [
            ("faithfulness",      faithfulness_m),
            ("answer_relevancy",  relevancy_m),
            ("context_precision", precision_m),
            ("context_recall",    recall_m),
        ]:
            try:
                s = asyncio.run(metric.single_turn_ascore(sample))
                rec[label] = round(s, 4)
                console.print(f"  {label}: {rec[label]}")
            except Exception as e:
                console.print(f"  [red]{label}: ERROR — {e}[/red]")
                rec[label] = None
        records.append(rec)

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["question", "answer", "ground_truth", "faithfulness", "answer_relevancy", "context_precision", "context_recall"])
        writer.writeheader()
        writer.writerows(records)
    console.print(f"\n[green]Results saved to {output}[/green]")

    table = Table(title="RAGAS Evaluation Result")
    table.add_column("Metric", style="cyan")
    table.add_column("Score", style="magenta", justify="right")
    for col in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        vals = [r[col] for r in records if r[col] is not None]
        avg = sum(vals) / len(vals) if vals else float("nan")
        table.add_row(col.replace("_", " ").title(), f"{avg:.3f}")
    console.print(table)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_fetch = sub.add_parser("fetch", help="Fetch answers from the running query service")
    p_fetch.add_argument("--api-key", required=True)
    p_fetch.add_argument("--golden", default="datasets/candidates.json")
    p_fetch.add_argument("--answers", default="datasets/answers_cache.json")

    p_score = sub.add_parser("score", help="Run RAGAS metrics on pre-fetched answers")
    p_score.add_argument("--answers", default="datasets/answers_cache.json")
    p_score.add_argument(
        "--output",
        default=f"results/ragas_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.csv",
    )

    args = parser.parse_args()
    if args.command == "fetch":
        fetch(args.api_key, args.golden, args.answers)
    else:
        score(args.answers, args.output)
