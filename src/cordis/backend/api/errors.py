from collections.abc import Awaitable, Callable
from typing import cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response

from cordis.backend.errors import CordisError


async def cordis_error_handler(_: Request, exc: CordisError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    handler = cast(Callable[[Request, Exception], Response | Awaitable[Response]], cordis_error_handler)
    app.add_exception_handler(CordisError, handler)
