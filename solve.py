#!/usr/bin/env python3
"""
Find the cheapest self serve plan per tool that covers a set of AI engines.

    python solve.py --engines chatgpt,perplexity,gemini,claude --prompts 100
    python solve.py --engines chatgpt,claude --prompts 50 --json
    python solve.py --list-engines

Every Peec AI alternative advertises an engine count. The count that matters is
how many of YOUR engines a plan covers without a sales call, and what the plan
costs once the add ons are in. This script answers that from tools.yaml.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent

ENGINES = {
    "chatgpt": "ChatGPT",
    "perplexity": "Perplexity",
    "gemini": "Gemini",
    "aio": "AI Overviews",
    "ai_mode": "AI Mode",
    "copilot": "Copilot",
    "claude": "Claude",
    "grok": "Grok",
    "deepseek": "DeepSeek",
    "meta": "Meta AI",
    "mistral": "Mistral",
    "qwen": "Qwen",
    "naver": "Naver AI",
}


def load(path: Path = ROOT / "tools.yaml") -> list[dict]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def fit_plan(plan: dict, need: set[str], prompts: int) -> dict:
    """Check one plan against the required engines and prompt count.

    Returns a dict with ok, cost (None when an add on price is unpublished),
    addons bought, and the engines or prompt cap that blocked it.
    """
    included = set(plan.get("included", []))
    pool = set(plan.get("pool", []))
    addon = set(plan.get("addon", []))
    choose = plan.get("choose", 0)

    missing = need - included
    picked = missing & pool
    missing -= picked
    overflow = max(0, len(picked) - choose)
    picked_addons = sorted(picked & addon)[:overflow] if overflow else []
    if overflow and len(picked_addons) < overflow:
        return {"ok": False, "why": f"needs {len(picked)} picks, plan allows {choose}"}

    bought = sorted(missing & addon) + picked_addons
    missing -= addon
    if missing:
        return {"ok": False, "blocked": sorted(missing)}

    cap = plan.get("prompts")
    if cap is not None and prompts > cap:
        return {"ok": False, "why": f"{cap} prompt cap"}

    cost = plan.get("price")
    if bought and cost is not None:
        each = plan.get("addon_price")
        if each is None:
            cost = None
        else:
            extra = each * len(bought)
            bundle = plan.get("addon_bundle")
            cost += min(extra, bundle) if bundle else extra
    return {"ok": True, "cost": cost, "addons": bought, "capped": cap is not None}


def solve_tool(tool: dict, need: set[str], prompts: int) -> dict:
    blocked: set[str] | None = None
    reasons = []
    for plan in tool["plans"]:
        r = fit_plan(plan, need, prompts)
        if r["ok"]:
            return {"tool": tool["name"], "id": tool["id"], "plan": plan["name"],
                    "currency": tool["currency"], "list_price": plan.get("price"), **r}
        # an engine is only truly blocked if no self serve plan offers it
        here = set(r.get("blocked", []))
        blocked = here if blocked is None else blocked & here
        if "why" in r:
            reasons.append(f"{plan['name']}: {r['why']}")
    blocked = blocked or set()
    gated = sorted(blocked & set(tool.get("enterprise", [])))
    absent = sorted(blocked - set(gated))
    return {"tool": tool["name"], "id": tool["id"], "ok": False,
            "enterprise": gated, "absent": absent, "reasons": reasons}


def solve(tools: list[dict], need: set[str], prompts: int) -> list[dict]:
    results = [solve_tool(t, need, prompts) for t in tools]

    def key(r: dict):
        if not r["ok"]:
            return (2, 0, r["tool"])
        if r["cost"] is None:
            return (1, r["list_price"] or 0, r["tool"])
        return (0, r["cost"], r["tool"])

    return sorted(results, key=key)


def money(value, currency: str) -> str:
    if value is None:
        return "usage priced"
    sign = "€" if currency == "EUR" else "$"
    return f"{sign}{value:,.2f}".replace(".00", "")


def describe(r: dict) -> tuple[str, str, str]:
    """Plan, monthly cost, note for one result row."""
    names = lambda ids: ", ".join(ENGINES[e] for e in ids)
    if not r["ok"]:
        parts = []
        if r["enterprise"]:
            parts.append(f"{names(r['enterprise'])} Enterprise only")
        if r["absent"]:
            parts.append(f"{names(r['absent'])} not offered")
        parts += r["reasons"][-1:] if not parts else []
        return "none", "n/a", ". ".join(parts)
    note = []
    if r["addons"]:
        note.append(f"add on: {names(r['addons'])}")
    if r["cost"] is None and r["list_price"] is not None:
        note.append("add on price not published")
    if not r["capped"]:
        note.append("prompt volume set by credits or config")
    cost = r["cost"] if r["cost"] is not None else r["list_price"]
    shown = money(cost, r["currency"])
    if r["cost"] is None and r["list_price"] is not None:
        shown = f"{shown} + add ons"
    return r["plan"], shown, ", ".join(note)


def markdown(results: list[dict]) -> str:
    rows = ["| Tool | Cheapest plan that fits | Monthly | Note |",
            "| --- | --- | --- | --- |"]
    for r in results:
        plan, cost, note = describe(r)
        rows.append(f"| {r['tool']} | {plan} | {cost} | {note} |")
    return "\n".join(rows)


def parse_engines(raw: str) -> set[str]:
    need = {e.strip() for e in raw.split(",") if e.strip()}
    unknown = need - ENGINES.keys()
    if unknown:
        sys.exit(f"unknown engine id: {', '.join(sorted(unknown))}. Try --list-engines")
    return need


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--engines", help="comma separated engine ids")
    ap.add_argument("--prompts", type=int, default=50)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--list-engines", action="store_true")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")

    if args.list_engines:
        for k, v in ENGINES.items():
            print(f"{k:<11}{v}")
        return 0
    if not args.engines:
        ap.error("--engines is required")

    results = solve(load(), parse_engines(args.engines), args.prompts)
    print(json.dumps(results, indent=2) if args.json else markdown(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
