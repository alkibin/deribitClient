"""HTTP-эндпоинты только для чтения, отдающие сохранённые индексные цены.

Каждый маршрут — ``GET`` и требует query-параметр ``ticker``.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from derbit_client.application.dto import PriceTickDTO
from derbit_client.application.price_query import PriceQueryService
from derbit_client.interfaces.api.deps import get_query_service
from derbit_client.interfaces.api.schemas import PriceTickSchema

router = APIRouter(prefix="/api/v1/prices", tags=["prices"])

TickerQuery = Query(..., min_length=1, description="Тикер, например 'btc_usd' или 'eth_usd'.")


@router.get("", response_model=list[PriceTickSchema])
async def get_all_prices(
    ticker: str = TickerQuery,
    service: PriceQueryService = Depends(get_query_service),
) -> list[PriceTickDTO]:
    """Вернуть все сохранённые цены для запрошенного тикера."""
    return await service.get_all_prices(ticker)


@router.get("/latest", response_model=PriceTickSchema)
async def get_latest_price(
    ticker: str = TickerQuery,
    service: PriceQueryService = Depends(get_query_service),
) -> PriceTickDTO:
    """Вернуть самую свежую цену для запрошенного тикера."""
    latest = await service.get_latest_price(ticker)
    if latest is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data for ticker '{ticker}'",
        )
    return latest


@router.get("/filter", response_model=list[PriceTickSchema])
async def get_prices_by_date(
    ticker: str = TickerQuery,
    date_from: int | None = Query(
        default=None,
        alias="from",
        ge=0,
        description="Включительная нижняя граница в виде UNIX timestamp (секунды).",
    ),
    date_to: int | None = Query(
        default=None,
        alias="to",
        ge=0,
        description="Включительная верхняя граница в виде UNIX timestamp (секунды).",
    ),
    service: PriceQueryService = Depends(get_query_service),
) -> list[PriceTickDTO]:
    """Вернуть цены для запрошенного тикера, отфильтрованные по диапазону (включительно)."""
    try:
        return await service.get_prices_between(ticker, start=date_from, end=date_to)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
