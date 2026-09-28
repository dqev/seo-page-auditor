#!/usr/bin/env python3
"""Batch-run audit.py over sites.txt lines START..END (1-indexed), never stopping.

Usage: python batch.py <start> <end>   (e.g. python batch.py 1 19)
Writes per-site JSON reports to bulk/<n>.json and appends one line per site
to bulk/results-<start>-<end>.jsonl with {n, url, query, exit, score, ...}.
A site that errors still gets a result line — the loop never stops.
"""
import json
import subprocess
import sys
import os

os.makedirs("bulk", exist_ok=True)

with open("sites.txt") as f:
    lines = [ln.strip() for ln in f if ln.strip()]

start, end = int(sys.argv[1]), int(sys.argv[2])
out_path = f"bulk/results-{start}-{end}.jsonl"
# fresh file for idempotent reruns
open(out_path, "w").close()

for i in range(start - 1, min(end, len(lines))):
    n = i + 1
    url, _, query = lines[i].partition("|")
    url, query = url.strip(), query.strip()
    dest = f"bulk/{n}.json"
    print(f"[{n}/{len(lines)}] {url} ...", flush=True)
    try:
        p = subprocess.run(
            [sys.executable, "audit.py", url, "--query", query,
             "--json", "--out", dest],
            capture_output=True, text=True, timeout=420)
        rec = {"n": n, "url": url, "query": query, "exit": p.returncode}
        if p.returncode == 0 and os.path.exists(dest):
            try:
                r = json.load(open(dest))
                rec.update({
                    "score": r.get("score"),
                    "rank": (r.get("search") or {}).get("rank"),
                    "words": (r.get("fetch") or {}).get("words"),
                    "fails": sum(1 for c in r.get("checks", []) if c["status"] == "FAIL"),
                    "skips": sum(1 for c in r.get("checks", []) if c["status"] == "SKIP"),
                })
            except Exception as e:
                rec["parse_error"] = str(e)[:200]
        else:
            rec["stderr"] = (p.stderr or p.stdout or "")[-300:]
        print(f"    -> exit={rec['exit']} score={rec.get('score')}", flush=True)
    except subprocess.TimeoutExpired:
        rec = {"n": n, "url": url, "query": query, "exit": "TIMEOUT"}
        print(f"    -> TIMEOUT", flush=True)
    except Exception as e:  # runner itself must never die
        rec = {"n": n, "url": url, "query": query, "exit": "RUNNER_ERROR",
               "stderr": str(e)[:300]}
        print(f"    -> RUNNER_ERROR {e}", flush=True)
    with open(out_path, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"DONE {start}-{end} -> {out_path}", flush=True)
