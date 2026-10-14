"""Исключения HTTP-слоя и централизованные обработчики ответов об ошибках.

Роутеры поднимают наследников :class:`ApiError` вместо ``HTTPException``;
:func:`register_exception_handlers` превращает их в единообразные JSON-ответы
вида ``{"detail": ...}``.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    """Базовое исключение API, несущее HTTP-статус и человекочитаемый текст."""

    status_code: int = 500

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class BadRequestError(ApiError):
    """Некорректный запрос клиента (HTTP 400)."""

    status_code = 400


class NotFoundError(ApiError):
    """Запрошенный ресурс отсутствует (HTTP 404)."""

    status_code = 404


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    """Вернуть единообразный JSON-ответ для любого :class:`ApiError`."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def register_exception_handlers(app: FastAPI) -> None:
    """Зарегистрировать обработчики исключений HTTP-слоя на приложении."""
    app.add_exception_handler(ApiError, api_error_handler)
