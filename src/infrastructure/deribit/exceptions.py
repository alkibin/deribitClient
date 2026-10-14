class DeribitError(RuntimeError):
    """Базовое исключение клиента Deribit."""


class DeribitNotFoundError(DeribitError):
    """Запрошенный ресурс не найден (HTTP 404, например неизвестный тикер)."""


class DeribitRateLimitError(DeribitError):
    """Превышен лимит запросов к Deribit (HTTP 429)."""


class DeribitServerError(DeribitError):
    """Ошибка на стороне сервера Deribit (HTTP 5xx)."""


class DeribitClientError(DeribitError):
    """Прочие ошибки запроса к Deribit (HTTP 4xx, кроме 404 и 429)."""
