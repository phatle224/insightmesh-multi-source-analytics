"""Request correlation without trusting arbitrary header content."""

import re
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Request, Response

REQUEST_ID_HEADER = "X-Request-ID"
SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


async def request_id_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    supplied = request.headers.get(REQUEST_ID_HEADER, "")
    request_id = supplied if SAFE_REQUEST_ID.fullmatch(supplied) else str(uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers[REQUEST_ID_HEADER] = request_id
    return response
