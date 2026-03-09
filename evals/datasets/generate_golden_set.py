"""
Generates candidate golden Q&A pairs from ingested documents.
Run once, then manually review and keep only high-quality pairs.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from runners.auth_client import AutoRefreshAuth

SEED_QUERIES = [
    "What is the CAP theorem?",
    "What is eventual consistency?",
    "What is the Paxos algorithm used for?",
    "What is a distributed hash table?",
    "What is the Raft consensus algorithm?",
    "What is a Byzantine fault in distributed systems?",
    "What is the two-phase commit protocol?",
    "What is consistent hashing?",
    "What is vector clock in distributed systems?",
    "What is the difference between synchronous and asynchronous replication?",
    "What is a consensus algorithm?",
    "What is the gossip protocol?",
    "What is a distributed ledger?",
    "What is partition tolerance?",
    "What is a quorum in distributed systems?",
    "What is MapReduce?",
    "What is a distributed transaction?",
    "What is sharding in databases?",
    "What is leader election in distributed systems?",
    "What is the CRDT data structure?",
]


def generate(api_key: str, output: str):
    # Resume from existing file if present
    output_path = Path(output)
    if output_path.exists():
        with open(output_path) as f:
            candidates = json.load(f)
        done_questions = {c["question"] for c in candidates}
        print(f"Resuming — {len(candidates)} already saved, {len(done_questions)} questions done.")
    else:
        candidates = []
        done_questions = set()

    auth = AutoRefreshAuth(api_key=api_key, base_url="http://localhost:8001")
    client = httpx.Client(auth=auth, timeout=180.0)

    remaining = [q for q in SEED_QUERIES if q not in done_questions]

    for i, question in enumerate(remaining, 1):
        print(f"[{i}/{len(remaining)}] {question}")
        try:
            response = client.post(
                "http://localhost:8001/v1/query",
                json={"text": question, "top_k": 5, "stream": False},
            )
            response.raise_for_status()
            data = response.json()
            candidates.append(
                {
                    "question": question,
                    "ground_truth": data["answer"],
                    "contexts": [s["title"] for s in data["sources"]],
                    "source_titles": [s["title"] for s in data["sources"]],
                    "review_status": "pending",
                }
            )
            # Save after every successful query — no progress lost on failure
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(candidates, f, indent=2)
            print(f"  -> saved ({len(candidates)} total)")
        except Exception as e:
            print(f"  ERROR: {e}")

    print(f"\nWrote {len(candidates)} candidates to {output}")
    print("Review each entry. Change 'review_status' to 'approved' to include in eval.")
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--output", default="evals/datasets/candidates.json")
    args = parser.parse_args()
    generate(args.api_key, args.output)
