# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException


def error_body(code: str, message: str, details: Optional[Any] = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}


def http_error(status: int, code: str, message: str, details: Optional[Any] = None) -> HTTPException:
    return HTTPException(status_code=status, detail=error_body(code, message, details))
