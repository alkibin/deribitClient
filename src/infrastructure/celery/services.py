import aiohttp

from src.application.price_ingestion import PriceIngestionService
from src.core.config import Settings
from src.infrastructure.db.repository import SqlAlchemyPriceRepository
from src.infrastructure.db.session import create_engine, create_session_factory, session_pool
from src.infrastructure.deribit.client import DeribitClient


async def fetch_and_store_prices(settings: Settings, tickers: list[str]) -> list[str]:
    """Загрузить текущие индексные цены и сохранить их в одной транзакции."""
    engine = create_engine(settings.postgres.dsn)
    session_factory = create_session_factory(engine)
    try:
        async with aiohttp.ClientSession() as http_session:
            provider = DeribitClient(
                session=http_session,
                base_url=settings.deribit.base_url,
                timeout=settings.deribit.timeout,
                max_retries=settings.deribit.max_retries,
            )
            async with session_pool(session_factory) as db_session:
                service = PriceIngestionService(
                    repository=SqlAlchemyPriceRepository(db_session),
                    provider=provider,
                )
                await service.fetch_and_store(tickers)
    finally:
        await engine.dispose()
