# derbitClient

Клиент криптобиржи [Deribit](https://docs.deribit.com/): раз в минуту забирает
текущий **index price** для `btc_usd` и `eth_usd`, сохраняет его в
**PostgreSQL** (тикер, цена, UNIX timestamp) и отдаёт сохранённые данные через
**FastAPI**.

Стек: Python 3.12 · FastAPI · Celery + Redis · PostgreSQL · SQLAlchemy 2.0
(async) + asyncpg · Alembic · pydantic-settings · aiohttp · uv.

## Запуск

### Docker

Поднимаются 5 контейнеров: `db` (PostgreSQL), `redis` (брокер), `app` (FastAPI),
`worker` и `beat` (Celery). `app` стартует после готовности БД (healthcheck в
compose) и применяет миграции Alembic перед запуском сервера.

```bash
cp .env.example .env
docker compose up --build
```

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Проверка здоровья: http://localhost:8000/health

Остановить и удалить данные:

```bash
docker compose down -v
```

В отдельных терминалах — воркер и расписание:


После этого раз в минуту будут сохраняться цены `btc_usd` и `eth_usd`.

## Design decisions

- **Clean Architecture (`domain / application / infrastructure / interfaces`)
  с зависимостями, направленными внутрь.** Домен не знает о фреймворках, поэтому
  бизнес-логика тестируется без БД и HTTP, а адаптеры (СУБД, биржа, брокер)
  меняются без правок домена.
- **Запись и чтение разделены на уровне сервисов.** `PriceIngestionService`
  (воркер Celery) и `PriceQueryService` (FastAPI) имеют разные зависимости и
  причины изменяться; API-слой не знает о Deribit и не создаёт клиент к бирже.
- **Порт IndexPriceProvider объявлен в application/ports.py,** реализация — в infrastructure. 
  Это инверсия зависимостей: application не импортирует infrastructure. 
  Источник цен можно подменить (другая биржа, заглушка в тестах), не меняя сервис.
- **Один контракт репозитория `PriceRepository`** (`add_many` / `get_all` /
  `get_latest` / `get_between` + `count*`) для чтения и записи. Разделение
  «чтение/запись» живёт в сервисах, а не в интерфейсе.
- **Устойчивость HTTP-клиента к сбоям.** Постоянные ошибки (4xx, кроме 429) не
  повторяются; временные (429, 5xx, сетевые) — через `tenacity` с
  экспоненциальной задержкой и джиттером (`reraise=True`).
- **Время — UNIX timestamp в секундах, составной индекс `(ticker, timestamp)`.**
  Timezone-agnostic, компактно, ускоряет «последняя цена» и выборку «за период».
- **Одна метка времени на батч.** Обе цены одного запуска задачи сохраняются с
  общим `observed_at`.
- **DI через конструкторы и FastAPI `Depends`; без глобальных мутабельных
  переменных.** Конфигурация и адаптеры живут в `app.state` и освобождаются в
  `lifespan`.
- **Асинхронный стек.** SQLAlchemy async + asyncpg, aiohttp только в
  ingestion-пути; воркер исполняет async-задачу через `asyncio.run`, ресурсы
  (engine, HTTP-сессия, транзакция) освобождаются в `finally`.
- **Пагинация в формате envelope `{items, total, limit, offset}`** на `/prices`
  и `/prices/filter`: явный контракт, легко документируется, не требует
  специальных заголовков.
- **Ошибки API — единый `{"detail": ...}`** через `interfaces/api/exceptions.py`
  (базовый `ApiError` → 400/404, обработчик в `app_factory`); 422 на валидации
  отдаёт сам FastAPI.
- **Конфигурация — pydantic-settings c `env_nested_delimiter="__"`
  (`POSTGRES__HOST`, `CELERY__BROKER_URL`).** Все настройки приходят из окружения
  и `.env`;
- **Миграции Alembic вместо `create_all`** — контролируемая эволюция схемы,
  применяются при старте `app`.
- **Миграции Alembic вместо `create_all`** — контролируемая эволюция схемы,
  применяются при старте `app`.
- **Docker Compose с 5 сервисами вместо минимальных двух.**
  Задание допускает два контейнера (приложение и БД), но Celery требует брокера и 
  отдельных процессов worker и beat. Один процесс — одна ответственность; 
  healthcheck БД гарантирует корректный порядок старта.

  