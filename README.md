# Сервис индексных цен Deribit

Сервис раз в минуту забирает index price `btc_usd` и `eth_usd` с [Deribit](https://docs.deribit.com/api-reference/market-data/public-get_index_price) и отдаёт сохранённые наблюдения через HTTP API.

Каждая запись хранит тикер, цену и время наблюдения в UNIX timestamp (секунды, UTC).

## Стек

- Python 3.12
- FastAPI — внешнее read-only API
- Celery и Redis — периодический сбор
- aiohttp — HTTP-клиент Deribit
- PostgreSQL и SQLAlchemy — хранение
- Alembic — схема базы
- Docker Compose — запуск

## Архитектура

Зависимости направлены внутрь: HTTP и Celery знают про сценарии, сценарии знают только про доменные порты, домен не знает про FastAPI, Celery, aiohttp и PostgreSQL.

```text
app/
  domain/            сущности, ошибки, порты репозитория, шлюза и часов
  application/       сценарии чтения и сбора цен
  infrastructure/    Deribit, PostgreSQL, Celery, настройки
  api/               FastAPI, схема ответов, сборка приложения
  worker.py          точка входа Celery
  collect_once.py    первый сбор при старте воркера
```

```mermaid
sequenceDiagram
    participant Beat as Celery Beat
    participant Worker as Celery worker
    participant Deribit
    participant DB as PostgreSQL
    participant API as FastAPI

    Beat->>Worker: collect_index_prices раз в минуту
    Worker->>Deribit: GET /public/get_index_price
    Deribit-->>Worker: index_price
    Worker->>DB: INSERT price_snapshots
    API->>DB: SELECT по ticker
```

Сборка зависимостей живёт в двух местах и больше нигде не создаёт клиентов и сессии:

- `create_app()` для HTTP-процесса
- `CollectIndexPricesJob` для одной задачи сбора

## Design decisions

### 1. Слои и объекты вместо общего состояния

Сценарий `PriceQueryService` получает репозиторий в конструктор. Сценарий `IngestIndexPrices` получает шлюз биржи, репозиторий и часы. Реализации (`SqlAlchemyPriceRepository`, `DeribitIndexPriceClient`, `SystemClock`) подставляются на краю процесса.

В домене и сценариях нет модульных настроек, engine и списков цен. Настройки читаются функцией `Settings.from_env()` в точке входа. Engine создаётся объектом `Database` и закрывается тем же объектом.

Исключение одно: `celery_app` в `app/worker.py`. Загрузчик Celery импортирует объект приложения из модуля (`celery -A app.worker:celery_app`). Это вход процесса, а не состояние бизнес-логики. Расписание и задача регистрируются фабрикой `create_worker()`.

### 2. Порты и реализации

`PriceRepository`, `IndexPriceGateway` и `Clock` — абстрактные классы. Сценарии зависят от них, а не от PostgreSQL и aiohttp. Подделки в тестах реализуют те же классы, поэтому unit-тесты не поднимают базу и не ходят в сеть.

Запись в базу обёрнута в `SqlAlchemyUnitOfWork`: одна сессия, commit при успехе, rollback при исключении, close в любом случае.

### 3. Что считается ценой и временем

Берётся поле `result.index_price` метода `public/get_index_price`. `estimated_delivery_price` не сохраняется: задание просит index price. В текущем ответе биржи нет `result.name`, поэтому в базу пишется индекс из запроса. Если поле `name` всё же пришло и не совпало с запросом, ответ отвергается.

Deribit не отдаёт отдельную метку времени самой цены, только служебные `usIn`/`usOut` запроса. В базу пишется момент наблюдения на нашей стороне, UNIX-секунды UTC. Оба тикера одного прогона получают один и тот же timestamp, чтобы снимки BTC и ETH были сопоставимы.

Повторный сбор в ту же секунду не создаёт вторую строку. Уникальный ключ `(ticker, recorded_at)` обновляет цену. Этот же индекс обслуживает выборку по тикеру и по диапазону времени, отдельный неуникальный индекс не нужен.

Цена хранится как `NUMERIC(24, 8)` и в коде как `Decimal`. JSON биржи разбирается через `parse_float=Decimal`, чтобы не проходить через двоичный `float`. В ответе API цена — строка, чтобы клиент не потерял точность.

### 4. aiohttp внутри синхронной задачи Celery

Клиент асинхронный: за один прогон оба индекса запрашиваются через `asyncio.gather`. Воркер Celery синхронный, поэтому `CollectIndexPricesJob` один раз вызывает `asyncio.run` на границе задачи. Клиент не ретраит HTTP сам. Повтор делает Celery, и только если не сохранился ни один тикер. Если упал один из двух, успешный снимок коммитится, а второй тикер будет взят на следующей минуте. Иначе ретрай всей задачи задублировал бы уже сохранённую цену.

Пул воркера — `solo`. Задача одна и упирается в сеть, процессы prefork не нужны. Engine создаётся на время задачи и закрывается в `finally`, чтобы не тащить соединения через перезапуск воркера.

### 5. Синхронный SQLAlchemy

Запись происходит раз в минуту, чтение — простые SELECT. Асинхронный драйвер не меняет устройство сценария и добавляет второй стиль сессий. HTTP наружу асинхронный, потому что этого требует клиент на aiohttp и потому что два запроса естественно выполняются параллельно. База остаётся синхронной.

### 6. Фильтр по дате

`GET /api/v1/prices/by-date` принимает календарный день `YYYY-MM-DD`. День без часового пояса читается как сутки UTC: полуинтервал `[00:00:00, следующие 00:00:00)`. UTC выбран потому, что timestamp в базе тоже UTC, а у биржи нет локальной зоны пользователя. Переход на летнее время на границу суток не влияет.

Пустой день — это `200` и `[]`. Отсутствие последней цены — `404`: «последней» записи нет, и пустой объект её не заменяет.

### 7. Тикер в API и список сбора

API не зашит на два тикера. Обязательный query-параметр `ticker` принимает индекс вида `btc_usd` (регистр и пробелы по краям нормализуются). Неверный формат — `422`.

Какие индексы собирать, решает `TRACKED_TICKERS`. По умолчанию это `btc_usd,eth_usd`. Смена интервала расписания требует перезапуска воркера: Beat читает его при старте. Список тикеров задача перечитывает на каждом запуске.

### 8. Контейнеры

Необязательное требование говорит про два контейнера: приложение и база. Celery без брокера не доставляет задачи, а PostgreSQL как брокер Celery официально не рекомендуется. Redis поэтому вынесен отдельно.

API и воркер — тоже разные контейнеры одного образа. Иначе планировщик живёт внутри процесса HTTP, и второй экземпляр API повторно ставит ту же минутную задачу. Beat запущен в единственном воркере с флагом `--beat`. Для этого сервиса отдельный контейнер Beat не нужен: экземпляр воркера один. Масштабировать воркер горизонтально при включённом Beat нельзя.

Итог: `api`, `worker`, `redis`, `db`. Это сознательный отход от формулировки «два контейнера» в пользу рабочего разделения очереди, планировщика и базы.

Миграции применяет только API, до того как он станет healthy. Воркер стартует после этого и сразу выполняет один сбор, не дожидаясь первой минуты Beat. Если Deribit на старте недоступен, процесс воркера всё равно поднимается, а следующая попытка приходит по расписанию.

Пагинации у «всех сохранённых данных» нет: метод по заданию возвращает полную историю тикера. На минутных снимках это примерно 1 440 строк на тикер в сутки. Для боевого объёма к этому методу понадобились бы `limit` и курсор; в контракт задания они не входят.

Ключи Deribit не используются. `public/get_index_price` публичный, секретов в репозитории нет.

## API

Интерактивная схема: `http://localhost:8000/docs`.

Все методы ниже — `GET`. Параметр `ticker` обязателен.

| Метод | Назначение |
| --- | --- |
| `/api/v1/prices?ticker=btc_usd` | Все сохранённые наблюдения, от старых к новым |
| `/api/v1/prices/latest?ticker=btc_usd` | Последняя цена |
| `/api/v1/prices/by-date?ticker=btc_usd&date=2026-10-14` | Наблюдения за календарный день UTC |

Ответ одного наблюдения:

```json
{
  "ticker": "btc_usd",
  "price": "63948.12",
  "timestamp": 1791936060
}
```

Списки возвращают JSON-массив таких объектов. `timestamp` — UNIX-секунды UTC.

Служебные маршруты, без `ticker`: `GET /health`, страница `/docs`.

Примеры:

```bash
curl "http://localhost:8000/api/v1/prices?ticker=btc_usd"
curl "http://localhost:8000/api/v1/prices/latest?ticker=eth_usd"
curl "http://localhost:8000/api/v1/prices/by-date?ticker=btc_usd&date=2026-10-14"
```

## Разворачивание в Docker

Нужны Docker и Docker Compose. Файл `.env` для Compose не требуется: переменные заданы в `docker-compose.yml`.

```bash
docker compose up --build -d
docker compose ps
```

API слушает `http://localhost:8000`. Когда `api` станет healthy, воркер сделает первый сбор. Проверка:

```bash
curl http://localhost:8000/health
curl "http://localhost:8000/api/v1/prices/latest?ticker=btc_usd"
```

Если последняя цена ещё `404`, смотрите лог воркера: до Deribit мог не дойти первый запрос.

```bash
docker compose logs -f api worker
```

Строки в базе:

```bash
docker compose exec db psql -U price -d prices \
  -c "select ticker, price, recorded_at from price_snapshots order by recorded_at desc limit 20;"
```

Остановка:

```bash
docker compose down
```

`docker compose down -v` удалит и том PostgreSQL.

Локальные учётные данные базы — `price` / `price`, база `prices`. Для стенда их нужно сменить в `docker-compose.yml` и в `DATABASE_URL`.

Образ один. API запускается через `docker/start-api.sh` (миграции, затем uvicorn). Воркер — через `docker/start-worker.sh` (первый сбор, затем Celery worker и Beat).

## Локальный запуск без контейнера приложения

Нужны Python 3.12, PostgreSQL и Redis.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Базу и Redis можно поднять отдельно:

```bash
docker compose up -d db redis
```

Дальше из корня репозитория, с активированным виртуальным окружением:

```bash
python -m alembic upgrade head
python -m uvicorn app.api.main:create_app --factory --reload --host 0.0.0.0 --port 8000
```

В другом терминале:

```bash
source .venv/bin/activate
python -m celery -A app.worker:celery_app worker --beat --loglevel=INFO --pool=solo
```

Разовый сбор без ожидания минуты:

```bash
python -m app.collect_once
```

Команды `alembic`, `uvicorn` и `celery` нужно запускать из корня проекта, чтобы импортировался пакет `app`.

## Переменные окружения

| Переменная | По умолчанию | Смысл |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://price:price@localhost:5432/prices` | Драйвер именно `postgresql+psycopg` (psycopg 3) |
| `REDIS_URL` | `redis://localhost:6379/0` | Брокер Celery. Результаты задач не хранятся |
| `DERIBIT_BASE_URL` | `https://www.deribit.com/api/v2` | Префикс публичного API |
| `TRACKED_TICKERS` | `btc_usd,eth_usd` | Индексы для минутного сбора |
| `PRICE_FETCH_INTERVAL_SECONDS` | `60` | Интервал Beat, читается при старте воркера |
| `HTTP_TIMEOUT_SECONDS` | `10` | Таймаут одного запроса к Deribit |

Пример лежит в `.env.example`.

## Тесты

Unit-тесты покрывают нормализацию тикера, разбор ответа Deribit, сценарий сбора (оба индекса, частичная и полная ошибка), фильтр по UTC-дню и три HTTP-метода. База и сеть для них не нужны: репозиторий и шлюз подменяются объектами.

```bash
source .venv/bin/activate
pytest
```

Репозиторий PostgreSQL и живой вызов Deribit unit-тестами не проверяются. Их закрывает запуск Compose и запросы из раздела про API.

## Схема таблицы

`price_snapshots`

| Колонка | Тип | Смысл |
| --- | --- | --- |
| `id` | `bigint identity` | Суррогатный ключ |
| `ticker` | `varchar(32)` | Индекс, например `btc_usd` |
| `price` | `numeric(24, 8)` | Index price, больше нуля |
| `recorded_at` | `bigint` | UNIX-секунды UTC, не меньше нуля |

Уникальность: `(ticker, recorded_at)`.
