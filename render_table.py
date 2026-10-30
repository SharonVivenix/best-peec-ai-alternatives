#!/usr/bin/env python3
"""
Regenerate both README tables from tools.yaml.

    python render_table.py            # print both blocks
    python render_table.py --write    # rewrite the blocks between the markers
    python render_table.py --check    # exit 1 if README and tools.yaml disagree

TABLE is the entry plan overview. FIT is solve.py run on the example
requirement below, so the worked example in the README can never go stale.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from solve import load, markdown, money, solve

ROOT = Path(__file__).resolve().parent
README = ROOT / "README.md"
EXAMPLE_ENGINES = {"chatgpt", "perplexity", "gemini", "claude"}
EXAMPLE_PROMPTS = 100
ACTION = {"report": "Reports", "prioritize": "Ranks opportunities", "execute": "Ships work"}


def engine_status(tool: dict, engine: str) -> str:
    """Where one engine first becomes available on a tool's self serve ladder."""
    for plan in tool["plans"]:
        if engine in plan.get("included", []):
            return f"included ({plan['name']})"
        if engine in plan.get("pool", []):
            return f"one of your picks ({plan['name']})"
        if engine in plan.get("addon", []):
            return f"add on ({plan['name']})"
    if engine in tool.get("enterprise", []):
        return "Enterprise only"
    return "not offered"


def entry_engines(plan: dict) -> str:
    if plan.get("choose"):
        return f"pick {plan['choose']} of {len(plan['pool'])}"
    inc, add = len(plan.get("included", [])), len(plan.get("addon", []))
    if not inc:
        return f"{add} as add ons"
    return f"{inc} + {add} add on" if add else str(inc)


def overview(tools: list[dict]) -> str:
    rows = ["| Tool | Entry plan | Price | Prompts | Engines on entry plan | Claude | After the data | Facts from |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for t in tools:
        p = t["plans"][0]
        prompts = p["prompts"] if p.get("prompts") is not None else "credits or config"
        rows.append(
            f"| [{t['name']}]({t['url']}) | {p['name']} | {money(p.get('price'), t['currency'])} "
            f"| {prompts} | {entry_engines(p)} | {engine_status(t, 'claude')} "
            f"| {ACTION[t['action']]} | {t['checked']} |")
    return "\n".join(rows)


def fit_block(tools: list[dict]) -> str:
    cmd = (f"python solve.py --engines {','.join(sorted(EXAMPLE_ENGINES))} "
           f"--prompts {EXAMPLE_PROMPTS}")
    return f"```bash\n{cmd}\n```\n\n" + markdown(solve(tools, EXAMPLE_ENGINES, EXAMPLE_PROMPTS))


def blocks() -> dict[str, str]:
    tools = load()
    return {"TABLE": overview(tools), "FIT": fit_block(tools)}


def apply(text: str, generated: dict[str, str]) -> str:
    for name, body in generated.items():
        pattern = re.compile(rf"(<!-- {name}:START -->\n).*?(\n<!-- {name}:END -->)", re.S)
        if not pattern.search(text):
            sys.exit(f"README is missing the {name} markers")
        text = pattern.sub(lambda m: m.group(1) + body + m.group(2), text)
    return text


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    generated = blocks()
    sys.stdout.reconfigure(encoding="utf-8")
    if not (args.write or args.check):
        print("\n\n".join(generated.values()))
        return 0
    current = README.read_text(encoding="utf-8")
    updated = apply(current, generated)
    if args.check:
        if current != updated:
            print("README tables are stale. Run: python render_table.py --write")
            return 1
        print("README tables match tools.yaml")
        return 0
    README.write_text(updated, encoding="utf-8", newline="\n")
    print("README tables rewritten")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
