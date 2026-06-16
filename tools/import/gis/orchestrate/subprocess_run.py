# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Optional

import sumolib

logger = logging.getLogger(__name__)


def _sumo_home() -> str:
    return os.environ.get(
        "SUMO_HOME",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")),
    )


def resolve_binary(name: str) -> str:
    return sumolib.checkBinary(name)


def resolve_tool_script(relative: str) -> str:
    return str(Path(_sumo_home()) / "tools" / relative)


def run_binary(
    binary: str,
    args: Iterable[str],
    cwd: Path,
    log_path: Optional[Path] = None,
) -> int:
    executable = resolve_binary(binary)
    cmd = [executable, *args]
    logger.info("binary=%s cwd=%s args=%s", executable, cwd, list(args))
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(f"CMD: {' '.join(cmd)}\n")
            proc = subprocess.run(
                cmd, cwd=str(cwd), stdout=log, stderr=subprocess.STDOUT, text=True, check=False
            )
        return proc.returncode
    proc = subprocess.run(cmd, cwd=str(cwd), check=False)
    return proc.returncode


def run_python_tool(
    script: str,
    args: Iterable[str],
    cwd: Path,
    log_path: Optional[Path] = None,
) -> int:
    cmd = [sys.executable, script, *args]
    logger.info("script=%s cwd=%s", script, cwd)
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(f"CMD: {' '.join(cmd)}\n")
            proc = subprocess.run(
                cmd, cwd=str(cwd), stdout=log, stderr=subprocess.STDOUT, text=True, check=False
            )
        return proc.returncode
    proc = subprocess.run(cmd, cwd=str(cwd), check=False)
    return proc.returncode


def save_and_run(
    binary: str,
    args: list[str],
    config_path: Path,
    cwd: Path,
    log_path: Path,
) -> int:
    cfg_args = args + ["--save-configuration", str(config_path.name)]
    code = run_binary(binary, cfg_args, cwd, log_path)
    if code != 0:
        return code
    return run_binary(binary, ["-c", str(config_path.name)], cwd, log_path)
