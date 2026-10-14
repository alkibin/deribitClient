# derbitClient

Клиент криптобиржи [Deribit](https://docs.deribit.com/), который каждую минуту
забирает текущий **index price** для `btc_usd` и `eth_usd`, сохраняет его в
**PostgreSQL** (тикер, цена, UNIX timestamp) и отдаёт сохранённые данные через
**FastAPI**.

## Содержание

- [Архитектура](#архитектура)
- [Стек](#стек)
- [Структура проекта](#структура-проекта)
- [Быстрый старт (Docker)](#быстрый-старт-docker)
- [Локальный запуск](#локальный-запуск)
- [API](#api)
- [Тесты и линтер](#тесты-и-линтер)
- [Конфигурация](#конфигурация)
- [Design decisions](#design-decisions)

## Архитектура

Проект построен по принципам **Clean Architecture** с направлением зависимостей
строго внутрь. Ответственности разделены по CQRS-подобному признаку: **запись**
(сбор цен) выполняет воркер Celery, **чтение** (запросы клиентов) — FastAPI.
```
   read  ┌─────────────┐   write
   ──────► PriceQuery  │   ┌─────────────── PriceIngestion ──┐
         │  Service    │   │  Service                        │
         └──────┬──────┘   └───────┬───────────────┬─────────┘
                │                  │               │
         PriceRepository ◄─────────┘       IndexPriceProvider (port)
                │                                  ▲
                └──── SqlAlchemyPriceRepository     │
                                    DeribitClient ───┘
        application ──► domain        infrastructure ─┘
```

- **domain** — чистые сущности (`PriceTick`) и контракт репозитория
  (`PriceRepository`). Не зависит ни от каких библиотек.
- **application** — сценарии и исходящие порты (`ports.IndexPriceProvider`):
  `PriceIngestionService` (fetch + store) и `PriceQueryService` (чтение).
  Зависит только от абстракций домена и собственных портов.
- **infrastructure** — адаптеры: SQLAlchemy-репозиторий, aiohttp-клиент
  Deribit, Celery, конфигурация. Реализует порты application/domain.
- **interfaces** — HTTP-слой: роутеры, Pydantic-схемы, DI-провайдеры, фабрика
  приложения. Зависит только от `PriceQueryService`.

## Стек

| Область            | Технология                                  |
| ------------------ | ------------------------------------------- |
| Язык               | Python 3.12                                 |
| HTTP API           | FastAPI + Uvicorn                           |
| HTTP-клиент        | aiohttp                                     |
| Периодические задачи | Celery + Celery Beat                      |
| Брокер             | Redis                                       |
| БД                 | PostgreSQL                                  |
| ORM                | SQLAlchemy 2.0 (async) + asyncpg            |
| Миграции           | Alembic                                     |
| Конфигурация       | pydantic-settings                           |
| Менеджер пакетов   | uv                                          |
| Тесты              | pytest + pytest-asyncio                     |

## Структура проекта

```
derbitClient/
├── derbit_client/
│   ├── domain/                    # сущности и контракты репозитория
│   │   ├── entities.py            # PriceTick
│   │   └── repositories.py        # PriceRepository (ABC)
│   ├── application/               # use cases и порты
│   │   ├── dto.py                 # PriceTickDTO
│   │   ├── ports.py               # IndexPriceProvider (Protocol)
│   │   ├── price_ingestion.py     # PriceIngestionService (write)
│   │   └── price_query.py         # PriceQueryService (read)
│   ├── infrastructure/
│   │   ├── config.py              # Settings (pydantic-settings)
│   │   ├── deribit/client.py      # DeribitClient (aiohttp)
│   │   ├── db/                    # base, models, session, repository, wait_for_db
│   │   └── celery/                # app (фабрика), tasks (fetch_index_prices)
│   └── interfaces/
│       └── api/
│           ├── app_factory.py
│           ├── deps.py
│           ├── schemas.py
│           └── routers/prices.py
├── alembic/                       # миграции
├── tests/                         # unit/integration тесты
├── docker/entrypoint.sh
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

## Быстрый старт (Docker)

Поднимаются 5 контейнеров: `db` (PostgreSQL), `redis` (брокер Celery),
`app` (FastAPI), `worker` (Celery worker), `beat` (Celery Beat). При старте
контейнер `app` ждёт готовности БД и применяет миграции Alembic.

```bash
docker compose up --build
```

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Проверка здоровья: http://localhost:8000/health

Остановить и удалить данные:

```bash
docker compose down -v
```

## Локальный запуск

1. Установите зависимости:

   ```bash
   uv sync --extra dev
   ```

2. Поднимите PostgreSQL и Redis (например, только эти сервисы из compose):

   ```bash
   docker compose up -d db redis
   ```

3. Создайте `.env` на основе примера и при необходимости отредактируйте:

   ```bash
   cp .env.example .env
   ```

4. Примените миграции:

   ```bash
   uv run alembic upgrade head
   ```

5. Запустите API:

   ```bash
   uv run uvicorn derbit_client.interfaces.api.app_factory:create_app --factory --reload
   ```

6. В отдельных терминалах запустите Celery worker и Beat:

   ```bash
   uv run celery -A derbit_client.infrastructure.celery.tasks worker --loglevel=info
   uv run celery -A derbit_client.infrastructure.celery.tasks beat --loglevel=info
   ```

После этого раз в минуту будут сохраняться цены `btc_usd` и `eth_usd`.

## API

Все методы — `GET`. У каждого обязательный query-параметр `ticker`.

### Получить все сохранённые данные по валюте

```bash
curl "http://localhost:8000/api/v1/prices?ticker=btc_usd"
```

### Получить последнюю цену валюты

```bash
curl "http://localhost:8000/api/v1/prices/latest?ticker=btc_usd"
```

Если данных нет — `404`.

### Получить цену с фильтром по дате

Границы `from` и `to` — UNIX timestamp (секунды), включительно; оба
необязательны.

```bash
curl "http://localhost:8000/api/v1/prices/filter?ticker=btc_usd&from=1700000000&to=1800000000"
```

Пример ответа:

```json
[
  { "ticker": "btc_usd", "price": "65432.10", "timestamp": 1700000123 }
]
```

## Тесты и линтер

```bash
uv run pytest
uv run ruff check .
```

Тесты не требуют внешней БД: сервисы ingestion/query, клиент Deribit и Celery
тестируются на фейках, репозиторий — на in-memory SQLite.

## Конфигурация

Все настройки задаются переменными окружения (см. `.env.example`). Вложенные
группы разделяются двойным подчёркиванием, например `POSTGRES__HOST`.

| Переменная                | По умолчанию                     | Описание                                  |
| ------------------------- | -------------------------------- | ----------------------------------------- |
| `DERIBIT__TICKERS`        | `btc_usd,eth_usd`                | Список тикеров                            |
| `DERIBIT__BASE_URL`       | `https://www.deribit.com/api/v2` | Базовый URL Deribit API                   |
| `DERIBIT__TIMEOUT`        | `10`                             | Таймаут HTTP-запросов, сек                |
| `DERIBIT__MAX_RETRIES`    | `3`                              | Число повторов при временных сбоях        |
| `DERIBIT__BACKOFF_BASE`   | `0.5`                            | Базовая задержка backoff, сек             |
| `DERIBIT__BACKOFF_MAX`    | `8.0`                            | Максимальная задержка backoff, сек        |
| `POSTGRES__HOST`          | `localhost`                      | Хост PostgreSQL                           |
| `POSTGRES__PORT`          | `5432`                           | Порт PostgreSQL                           |
| `POSTGRES__USER`          | `derbit`                         | Пользователь БД                           |
| `POSTGRES__PASSWORD`      | `derbit`                         | Пароль БД                                 |
| `POSTGRES__DB`            | `derbit`                         | Имя БД                                    |
| `CELERY__BROKER_URL`      | `redis://localhost:6379/0`       | Брокер Celery                             |
| `CELERY__RESULT_BACKEND`  | `redis://localhost:6379/1`       | Result backend Celery                     |
| `CELERY__FETCH_CRON`      | `* * * * *`                      | Cron-расписание сбора цен                 |
| `CELERY__TIMEZONE`        | `UTC`                            | Часовой пояс Celery                       |

## Design decisions

- **Clean Architecture со слоями `domain / application / infrastructure /
  interfaces`.** Домен не знает о фреймворках; зависимости направлены внутрь.
  Это позволяет тестировать бизнес-логику без БД и HTTP, а также менять
  адаптеры (СУБД, клиент биржи, брокер) без изменений в домене.
- **Разделение записи и чтения.** Сбор цен (`PriceIngestionService`, вызывается
  воркером Celery) и обслуживание клиентов (`PriceQueryService`, вызывается
  FastAPI) — разные сервисы с разными зависимостями и причинами изменяться.
  API-слой не знает о Deribit и не создаёт HTTP-клиент к бирже.
- **Порт `IndexPriceProvider` объявлен в `application/ports.py`** и реализуется
  инфраструктурой (`DeribitClient`). Порт принадлежит слою, который его
  использует, поэтому `application` не импортирует `infrastructure` — вектор
  зависимостей указывает строго внутрь.
- **Единый контракт репозитория `PriceRepository`.** Сбор и чтение цен работают
  с одним шлюзом (`add_many` / `get_all` / `get_latest` / `get_between`), который
  реализует `SqlAlchemyPriceRepository`. Разделение «чтение/запись» на уровне
  сервисов сохранено, а искусственное расщепление интерфейса не вводится.
- **Устойчивость HTTP-клиента к сбоям Deribit.** `DeribitClient` различает
  постоянные ошибки (404 и прочие 4xx — без повторов) и временные (429, 5xx,
  сетевые сбои). Временные повторяются через библиотеку `tenacity` с
  экспоненциальной задержкой и джиттером; для 429 приоритет отдаётся заголовку
  `Retry-After`.
- **Инъекция зависимостей через конструкторы и FastAPI `Depends`.** Никаких
  глобальных переменных: конфигурация и адаптеры создаются в фабрике приложения
  и живут в `app.state`, освобождаются в `lifespan`.
- **Хранение времени как `BigInteger` UNIX timestamp.** Требование ТЗ,
  timezone-agnostic, компактно, быстро фильтруется на уровне БД. Составной
  индекс `(ticker, timestamp)` ускоряет выборки «последняя цена» и «за период».
- **Одна метка времени на батч.** В рамках одного запуска задачи обе цены
  (`btc_usd`, `eth_usd`) сохраняются с одинаковым `timestamp` — это даёт
  согласованный срез рынка.
- **aiohttp для клиента, SQLAlchemy async + asyncpg для БД.** Стек полностью
  асинхронный, что соответствует природе I/O-нагрузки. aiohttp используется
  только в ingestion-пути (Celery), FastAPI его не требует.
- **Celery worker выполняет async-код через `asyncio.run` внутри задачи.**
  Каждый запуск создаёт собственные engine, HTTP-сессию и scope транзакции,
  которые гарантированно освобождаются в `finally`.
- **Фильтр по дате — включительный диапазон `from`/`to` в UNIX timestamp.**
  Предсказуемая семантика; значения валидируются (`0 <= from <= to` → иначе
  `422`).
- **Миграции Alembic вместо `create_all`.** Контролируемая эволюция схемы и
  воспроизводимый деплой; применяются автоматически при старте контейнера.
- **SQLite (через `aiosqlite`) только в тестах.** Модель использует
  `BigInteger().with_variant(Integer, "sqlite")`, чтобы автоинкрементный
  первичный ключ работал и в тестах, и в проде, без дублирования моделей.
