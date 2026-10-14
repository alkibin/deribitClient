"""HTTP-эндпоинты только для чтения, отдающие сохранённые индексные цены."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from src.application.dto import PriceTickDTO, Page
from src.application.price_query import PriceQueryService
from src.interfaces.api import schemas
from src.interfaces.api.di import get_query_service
from src.interfaces.api.exceptions import NotFoundError

router = APIRouter(prefix="/api/v1/prices", tags=["prices"])


@router.get("", response_model=schemas.PricePageSchema)
async def get_all_prices(
    query: Annotated[schemas.PriceListQuery, Query()],
    service: PriceQueryService = Depends(get_query_service),
) -> Page[PriceTickDTO]:
    """Вернуть страницу сохранённых цен для запрошенного тикера."""
    return await service.get_all_prices(query.ticker, limit=query.limit, offset=query.offset)


@router.get("/latest", response_model=schemas.PriceTickSchema)
async def get_latest_price(
    query: Annotated[schemas.PriceLatestQuery, Query()],
    service: PriceQueryService = Depends(get_query_service),
) -> PriceTickDTO:
    """Вернуть самую свежую цену для запрошенного тикера."""
    latest = await service.get_latest_price(query.ticker)
    if latest is None:
        raise NotFoundError(f"No data for ticker '{query.ticker}'")
    return latest


@router.get("/filter", response_model=schemas.PricePageSchema)
async def get_prices_by_date(
    query: Annotated[schemas.PriceFilterQuery, Query()],
    service: PriceQueryService = Depends(get_query_service),
) -> Page[PriceTickDTO]:
    """Вернуть страницу цен тикера, отфильтрованных по диапазону (включительно)."""
    return await service.get_prices_between(
        query.ticker,
        start=query.date_from,
        end=query.date_to,
        limit=query.limit,
        offset=query.offset,
    )
