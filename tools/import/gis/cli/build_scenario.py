# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

"""Build a runnable VISUM scenario (demand + assignment).

One-line invocation (from repo root)::

    set PYTHONPATH=tools;tools\\import
    python -m gis.cli.build_scenario --workspace c:\\tmp\\karlsruhe ^
        --scenario-id karlsruhe --assignment-method duarouter

Environment defaults: ``KARLSRUHE_OMX``, ``KARLSRUHE_SQLITE``, ``KARLSRUHE_NET``.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from gis.orchestrate.assignment import AssignmentMethod, AssignmentOptions
from gis.orchestrate.scenario import RunnableScenarioOptions, build_runnable_scenario


def _env_path(name: str) -> str | None:
    value = os.environ.get(name)
    return value if value else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build VISUM OMX demand and SUMO routes.")
    parser.add_argument("--workspace", required=True, help="Scenario workspace root")
    parser.add_argument("--omx", default=_env_path("KARLSRUHE_OMX"), help="OMX matrix path")
    parser.add_argument("--sqlite", default=_env_path("KARLSRUHE_SQLITE"), help="VISUM SQLite path")
    parser.add_argument("--net", default=_env_path("KARLSRUHE_NET"), help="Built net.xml path")
    parser.add_argument("--scenario-id", default="scenario", help="sumocfg base name")
    parser.add_argument(
        "--assignment-method",
        choices=[m.value for m in AssignmentMethod],
        default=AssignmentMethod.DUAROUTER.value,
        help="duarouter (fast) or duaIterate (dynamic assignment)",
    )
    parser.add_argument("--iterations", type=int, default=2, help="duaIterate last step")
    parser.add_argument("--begin", type=int, default=0)
    parser.add_argument("--end", type=int, default=7200)
    parser.add_argument("--no-sumocfg", action="store_true", help="Skip sim/*.sumocfg emission")
    parser.add_argument("--copy-sources", action="store_true", help="Copy OMX/SQLite into sources/")
    args = parser.parse_args(argv)

    missing = [
        label
        for label, value in (("omx", args.omx), ("sqlite", args.sqlite), ("net", args.net))
        if not value
    ]
    if missing:
        parser.error(f"missing required inputs: {', '.join(missing)}")

    options = RunnableScenarioOptions(
        scenario_id=args.scenario_id,
        assignment=AssignmentOptions(
            method=AssignmentMethod(args.assignment_method),
            iterations=args.iterations,
            begin=args.begin,
            end=args.end,
        ),
        emit_sumocfg=not args.no_sumocfg,
        copy_sources=args.copy_sources,
    )
    result = build_runnable_scenario(
        args.omx,
        args.sqlite,
        args.net,
        args.workspace,
        options,
    )
    print(f"rebuild_plan={result.rebuild_plan.value}")
    for message in result.messages:
        print(message)
    if result.assignment:
        print(f"routes={result.assignment.routes_path}")
    if result.sumocfg_path:
        print(f"sumocfg={result.sumocfg_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
