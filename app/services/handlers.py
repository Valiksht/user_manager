from fastapi import Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    status_code = 400

    def __init__(self, detail: str):
        self.detail = detail


class NotFoundItemException(AppException):
    status_code = 404


class PermissionDeniedException(AppException):
    status_code = 403


async def app_exception_handler(
    request: Request,
    exc: AppException,
):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            'detail': str(exc),
        },
    )
