"""HTTP-эндпоинты только для чтения, отдающие сохранённые индексные цены."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.application.dto import PriceTickDTO
from src.application.price_query import PriceQueryService
from src.interfaces.api.di import get_query_service
from src.interfaces.api.exceptions import NotFoundError
from src.interfaces.api.schemas import (
    PriceFilterQuery,
    PriceLatestQuery,
    PriceListQuery,
    PricePageSchema,
    PriceTickSchema,
)

router = APIRouter(prefix="/api/v1/prices", tags=["prices"])


@router.get("", response_model=PricePageSchema)
async def get_all_prices(
    query: Annotated[PriceListQuery, Query()],
    service: PriceQueryService = Depends(get_query_service),
) -> PricePageSchema:
    """Вернуть страницу сохранённых цен для запрошенного тикера."""
    page = await service.get_all_prices(query.ticker, limit=query.limit, offset=query.offset)
    return PricePageSchema(
        items=page.items,
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/latest", response_model=PriceTickSchema)
async def get_latest_price(
    query: Annotated[PriceLatestQuery, Query()],
    service: PriceQueryService = Depends(get_query_service),
) -> PriceTickDTO:
    """Вернуть самую свежую цену для запрошенного тикера."""
    latest = await service.get_latest_price(query.ticker)
    if latest is None:
        raise NotFoundError(f"No data for ticker '{query.ticker}'")
    return latest


@router.get("/filter", response_model=PricePageSchema)
async def get_prices_by_date(
    query: Annotated[PriceFilterQuery, Query()],
    service: PriceQueryService = Depends(get_query_service),
) -> PricePageSchema:
    """Вернуть страницу цен тикера, отфильтрованных по диапазону (включительно)."""
    page = await service.get_prices_between(
        query.ticker,
        start=query.date_from,
        end=query.date_to,
        limit=query.limit,
        offset=query.offset,
    )
    return PricePageSchema(
        items=page.items,
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )
