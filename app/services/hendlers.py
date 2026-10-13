from fastapi import Request
from fastapi.responses import JSONResponse


class AppExeption(Exception):
    status_code = 400

    def __init__(self, detail: str):
        self.detail = detail


class NotFoundItemExeption(AppExeption):
    status_code = 404


class PermissionDeniedExeption(AppExeption):
    status_code = 403


async def app_exeprion_hendler(
    request: Request,
    exc: AppExeption,
):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            'detail': str(exc),
        },
    )
