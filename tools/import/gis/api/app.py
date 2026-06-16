# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, FastAPI, File, Form, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from gis.api.errors import error_body, http_error
from gis.normalize import BuildOptions
from gis.orchestrate import build_scenario, run_simulation
from gis.workspace import BuildState, ScenarioPaths, StatusStore, workspace_root

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 500 * 1024 * 1024
router = APIRouter(prefix="/v1")


def _ensure_scenario(scenario_id: str) -> ScenarioPaths:
    paths = ScenarioPaths(scenario_id=scenario_id, root=workspace_root() / scenario_id)
    if not paths.root.exists():
        raise http_error(404, "scenario_not_found", f"Unknown scenario {scenario_id}")
    return paths


def _enqueue_build(scenario_id: str, options: BuildOptions) -> None:
    try:
        build_scenario(scenario_id, options)
    except Exception as exc:
        logger.exception("background build failed scenario_id=%s", scenario_id)


def _enqueue_run(scenario_id: str, run_id: str) -> None:
    try:
        run_simulation(scenario_id, run_id)
    except Exception as exc:
        logger.exception("background run failed scenario_id=%s run_id=%s", scenario_id, run_id)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/scenarios", status_code=202)
async def create_scenario(
    background_tasks: BackgroundTasks,
    build_options: Optional[str] = Form(default=None),
    layer: Optional[str] = Query(default=None),
    files: list[UploadFile] = File(...),
) -> dict[str, str]:
    scenario_id = str(uuid.uuid4())
    paths = ScenarioPaths.create(scenario_id)
    options = BuildOptions.from_dict(json.loads(build_options) if build_options else None)
    manifest: list[dict[str, Any]] = []

    for upload in files:
        data = await upload.read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise http_error(
                413,
                "upload_too_large",
                f"File {upload.filename} exceeds 500 MB limit",
            )
        filename = upload.filename or "upload.bin"
        dest = paths.inputs / filename
        dest.write_bytes(data)
        entry: dict[str, Any] = {"filename": filename, "role": _role_for(filename)}
        if layer and filename.lower().endswith(".gpkg"):
            entry["layer"] = layer
        manifest.append(entry)

    (paths.inputs / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    background_tasks.add_task(_enqueue_build, scenario_id, options)
    return {"scenario_id": scenario_id}


@router.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: str) -> dict[str, Any]:
    paths = _ensure_scenario(scenario_id)
    store = StatusStore(paths.status_file)
    return {"scenario_id": scenario_id, "workspace": str(paths.root), "build": store.get_build().to_dict()}


@router.get("/scenarios/{scenario_id}/status")
def get_status(scenario_id: str) -> dict[str, Any]:
    paths = _ensure_scenario(scenario_id)
    return StatusStore(paths.status_file).get_build().to_dict()


@router.get("/scenarios/{scenario_id}/artifacts")
def list_artifacts(scenario_id: str, name: Optional[str] = Query(default=None)):
    paths = _ensure_scenario(scenario_id)
    if name:
        target = paths.root / name
        if not target.is_file():
            raise http_error(404, "artifact_not_found", f"Artifact {name} not found")
        return FileResponse(target)
    return {"artifacts": paths.list_artifacts()}


@router.post("/scenarios/{scenario_id}/run", status_code=202)
def start_run(scenario_id: str, background_tasks: BackgroundTasks) -> dict[str, str]:
    paths = _ensure_scenario(scenario_id)
    store = StatusStore(paths.status_file)
    if store.get_build().state != BuildState.READY:
        raise http_error(409, "invalid_state", "Scenario build is not ready")
    run_id = str(uuid.uuid4())
    background_tasks.add_task(_enqueue_run, scenario_id, run_id)
    return {"run_id": run_id}


@router.get("/scenarios/{scenario_id}/runs/{run_id}")
def get_run(scenario_id: str, run_id: str) -> dict[str, Any]:
    paths = _ensure_scenario(scenario_id)
    store = StatusStore(paths.status_file)
    run = store.get_run(run_id)
    if run is None:
        raise http_error(404, "run_not_found", f"Unknown run {run_id}")
    return run.to_dict()


def _role_for(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".omx"):
        return "omx"
    if "zone" in lower:
        return "zones"
    return "roads"


def create_app() -> FastAPI:
    app = FastAPI(title="SUMO GIS API", version="0.1.0", openapi_url="/v1/openapi.json")
    app.include_router(router)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request, exc):  # type: ignore[no-untyped-def]
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body("http_error", str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def unhandled(request, exc):  # type: ignore[no-untyped-def]
        logger.exception("unhandled error")
        return JSONResponse(status_code=500, content=error_body("internal_error", str(exc)))

    return app
