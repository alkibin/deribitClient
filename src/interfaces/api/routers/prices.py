"""HTTP-эндпоинты только для чтения, отдающие сохранённые индексные цены."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.application.dto import PriceTickDTO
from src.application.price_query import PriceQueryService
from src.interfaces.api.di import get_query_service
from src.interfaces.api.schemas import PriceTickSchema, PriceFilterSchema

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
    filters: PriceFilterSchema = Depends(),
    service: PriceQueryService = Depends(get_query_service),
) -> list[PriceTickDTO]:
    """Вернуть цены для запрошенного тикера, отфильтрованные по диапазону (включительно)."""
    return await service.get_prices_between(ticker, start=filters.date_from, end=filters.date_to)
