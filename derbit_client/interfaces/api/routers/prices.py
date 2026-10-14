"""Read-only HTTP endpoints exposing stored index prices.

Every route is a ``GET`` and requires the ``ticker`` query parameter.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from derbit_client.application.dto import PriceTickDTO
from derbit_client.application.price_query import PriceQueryService
from derbit_client.interfaces.api.deps import get_query_service
from derbit_client.interfaces.api.schemas import PriceTickSchema

router = APIRouter(prefix="/api/v1/prices", tags=["prices"])

TickerQuery = Query(..., min_length=1, description="Ticker, e.g. 'btc_usd' or 'eth_usd'.")


@router.get("", response_model=list[PriceTickSchema])
async def get_all_prices(
    ticker: str = TickerQuery,
    service: PriceQueryService = Depends(get_query_service),
) -> list[PriceTickDTO]:
    """Return every stored price for the requested ticker."""
    return await service.get_all_prices(ticker)


@router.get("/latest", response_model=PriceTickSchema)
async def get_latest_price(
    ticker: str = TickerQuery,
    service: PriceQueryService = Depends(get_query_service),
) -> PriceTickDTO:
    """Return the most recent price for the requested ticker."""
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
        description="Inclusive lower bound as a UNIX timestamp (seconds).",
    ),
    date_to: int | None = Query(
        default=None,
        alias="to",
        ge=0,
        description="Inclusive upper bound as a UNIX timestamp (seconds).",
    ),
    service: PriceQueryService = Depends(get_query_service),
) -> list[PriceTickDTO]:
    """Return prices for the requested ticker filtered by an inclusive date range."""
    try:
        return await service.get_prices_between(ticker, start=date_from, end=date_to)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
