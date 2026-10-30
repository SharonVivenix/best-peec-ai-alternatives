#!/usr/bin/env python3
"""
Plan a Peec AI agency credit pool before you buy one, or before you leave.

    python peec_credits.py examples/clients.example.csv
    python peec_credits.py examples/clients.example.csv --plus-model acme-dental

Peec agency plans sell a pool of credits that you allocate across client
projects. The rules, from peec.ai/pricing-agencies (checked 30 October 2026):

    1 prompt x 1 model x 1 day = 1 credit, so 30 credits per prompt per model
    minimum allocation per project is 900 credits
    credits are allocation slots, they do not reset or expire
    Essential 10,000, Growth 25,000, Scale 65,000

Input CSV columns: client,prompts,models
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

DAYS = 30
PROJECT_MIN = 900
POOLS = [("Essential", 10_000), ("Growth", 25_000), ("Scale", 65_000)]


def allocation(prompts: int, models: int) -> int:
    return max(PROJECT_MIN, prompts * models * DAYS)


def smallest_pool(total: int) -> tuple[str, int] | None:
    return next(((n, c) for n, c in POOLS if c >= total), None)


def read_clients(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return [{"client": r["client"].strip(), "prompts": int(r["prompts"]),
                 "models": int(r["models"])} for r in csv.DictReader(fh)]


def plan(clients: list[dict], plus_model: str | None = None) -> list[dict]:
    rows = []
    for c in clients:
        models = c["models"] + (1 if c["client"] == plus_model else 0)
        raw = c["prompts"] * models * DAYS
        rows.append({**c, "models": models, "raw": raw,
                     "credits": allocation(c["prompts"], models),
                     "floored": raw < PROJECT_MIN})
    return rows


def report(rows: list[dict]) -> str:
    out = [f"{'client':<22}{'prompts':>8}{'models':>8}{'credits':>9}"]
    for r in rows:
        flag = "  (900 minimum)" if r["floored"] else ""
        out.append(f"{r['client']:<22}{r['prompts']:>8}{r['models']:>8}{r['credits']:>9,}{flag}")
    total = sum(r["credits"] for r in rows)
    out.append(f"{'total':<38}{total:>9,}")
    pool = smallest_pool(total)
    if pool:
        name, cap = pool
        out.append(f"\nfits {name} ({cap:,}), {cap - total:,} credits of headroom "
                   f"= {(cap - total) // (3 * DAYS)} more prompts at 3 models")
    else:
        out.append(f"\nexceeds Scale ({POOLS[-1][1]:,}), needs a custom plan")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Peec AI agency credit planner")
    ap.add_argument("csv", type=Path)
    ap.add_argument("--plus-model", metavar="CLIENT",
                    help="show the pool after adding one model to this client")
    args = ap.parse_args(argv)

    clients = read_clients(args.csv)
    print(report(plan(clients)))
    if args.plus_model:
        if args.plus_model not in {c["client"] for c in clients}:
            ap.error(f"no client named {args.plus_model}")
        print(f"\nwith one more model on {args.plus_model}:\n")
        print(report(plan(clients, args.plus_model)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
