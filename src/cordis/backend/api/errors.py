import logging
from collections.abc import Awaitable, Callable
from typing import cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response

from cordis.backend.errors import CordisError

logger = logging.getLogger(__name__)


async def cordis_error_handler(request: Request | None, exc: CordisError) -> JSONResponse:
    request_path = "<unknown>" if request is None else str(request.url.path)
    logger.error(
        "Cordis error handled path=%s status=%s code=%s message=%s",
        request_path,
        exc.status_code,
        exc.code,
        exc.message,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    handler = cast(Callable[[Request, Exception], Response | Awaitable[Response]], cordis_error_handler)
    app.add_exception_handler(CordisError, handler)
