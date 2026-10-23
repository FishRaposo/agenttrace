"""Launch the same credential-free workload used by the local dashboard.

Run from an installed SDK, including outside this checkout. No provider calls.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from agenttrace.portfolio import run_workload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario", choices=("incident", "repaired"), default="incident"
    )
    parser.add_argument("--endpoint", default="http://127.0.0.1:8300")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = asyncio.run(run_workload(args.scenario, endpoint=args.endpoint))
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result["delivery"]["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
