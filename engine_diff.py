#!/usr/bin/env python3
"""
Decide which engines are worth paying for before you compare tools.

    python engine_diff.py examples/manual-checks.example.csv
    python engine_diff.py my-checks.csv --threshold 0.6

Input is a CSV you fill by hand: run five to ten buying intent prompts on each
engine and write down the brands each answer recommends.

    prompt,engine,brands
    best crm for startups,chatgpt,Acme|Northwind|Globex

For every pair of engines the script averages the Jaccard overlap of their
brand lists across prompts. Two engines that keep naming the same brands are
one signal billed twice. The output is the smallest engine set that still
covers every distinct answer pattern, printed as a ready solve.py command.
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from itertools import combinations
from pathlib import Path


def read_checks(path: Path) -> dict[str, dict[str, set[str]]]:
    """engine -> prompt -> set of lowercased brand names."""
    data: dict[str, dict[str, set[str]]] = defaultdict(dict)
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            brands = {b.strip().lower() for b in row["brands"].split("|") if b.strip()}
            data[row["engine"].strip()][row["prompt"].strip()] = brands
    return dict(data)


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def similarity(data: dict[str, dict[str, set[str]]]) -> dict[tuple[str, str], float]:
    """Mean Jaccard per engine pair over the prompts both engines answered."""
    out = {}
    for x, y in combinations(sorted(data), 2):
        shared = data[x].keys() & data[y].keys()
        if shared:
            out[(x, y)] = sum(jaccard(data[x][p], data[y][p]) for p in shared) / len(shared)
    return out


def pick(data: dict, sim: dict, threshold: float) -> tuple[list[str], dict[str, str]]:
    """Greedy: most distinct engine first, skip any engine a pick already mirrors."""
    def s(a: str, b: str) -> float:
        return sim.get((min(a, b), max(a, b)), 0.0)

    engines = sorted(data)
    mean = {e: sum(s(e, o) for o in engines if o != e) / max(1, len(engines) - 1) for e in engines}
    chosen: list[str] = []
    mirrored: dict[str, str] = {}
    for e in sorted(engines, key=lambda e: (mean[e], e)):
        twin = next((c for c in chosen if s(e, c) >= threshold), None)
        if twin:
            mirrored[e] = twin
        else:
            chosen.append(e)
    return chosen, mirrored


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="engine overlap from manual prompt checks")
    ap.add_argument("csv", type=Path)
    ap.add_argument("--threshold", type=float, default=0.7,
                    help="mean overlap at which two engines count as one (default 0.7)")
    args = ap.parse_args(argv)

    data = read_checks(args.csv)
    sim = similarity(data)
    engines = sorted(data)
    width = max(len(e) for e in engines) + 2

    print("Mean brand overlap (Jaccard, 1.00 = identical lists)\n")
    print(" " * width + "".join(f"{e:>{width}}" for e in engines))
    for a in engines:
        cells = []
        for b in engines:
            v = 1.0 if a == b else sim.get((min(a, b), max(a, b)))
            cells.append(f"{v:>{width}.2f}" if v is not None else f"{'n/a':>{width}}")
        print(f"{a:<{width}}" + "".join(cells))

    chosen, mirrored = pick(data, sim, args.threshold)
    print()
    for e, twin in sorted(mirrored.items()):
        print(f"skip {e}: mirrors {twin}")
    prompts = len({p for per in data.values() for p in per})
    print(f"\nkeep {len(chosen)} of {len(engines)} engines\n")
    print(f"python solve.py --engines {','.join(sorted(chosen))} --prompts {max(prompts, 50)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
