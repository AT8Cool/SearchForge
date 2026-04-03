import asyncio
import logging
import os
import threading
from collections import OrderedDict
from contextlib import asynccontextmanager
from dataclasses import dataclass
from time import monotonic, perf_counter

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from app.core.settings import get_db_path
from app.core.search import refresh_search_cache, run_search

CACHE_TTL_SECONDS = 600.0
CACHE_MAX_ENTRIES = 512
SEARCH_CONCURRENCY_LIMIT = max(8, (os.cpu_count() or 2) * 4)
DB_REFRESH_CHECK_INTERVAL_SECONDS = 30.0
LOG_QUERY_MAX_LENGTH = 120
DB_PATH = get_db_path()

LOGGER = logging.getLogger("search_api")
if not LOGGER.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    LOGGER.addHandler(handler)
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False


@dataclass(slots=True)
class CacheEntry:
    value: tuple
    expires_at: float


class LruTtlCache:
    def __init__(self, max_entries: int, ttl_seconds: float) -> None:
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._entries: OrderedDict[str, CacheEntry] = OrderedDict()
        self._inflight: dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()

    def _evict_expired_locked(self, now: float) -> None:
        expired_keys = [
            key for key, entry in self._entries.items()
            if entry.expires_at <= now
        ]
        for key in expired_keys:
            self._entries.pop(key, None)

    def _evict_lru_locked(self) -> None:
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)

    async def clear(self) -> None:
        async with self._lock:
            self._entries.clear()

    async def get_or_load(self, key: str, loader):
        now = monotonic()

        async with self._lock:
            self._evict_expired_locked(now)
            cached = self._entries.get(key)
            if cached is not None:
                self._entries.move_to_end(key)
                return cached.value, "hit"

            inflight = self._inflight.get(key)
            if inflight is None:
                inflight = asyncio.get_running_loop().create_future()
                self._inflight[key] = inflight
                should_load = True
            else:
                should_load = False

        if not should_load:
            return await inflight, "shared"

        try:
            value = await loader()
        except Exception as exc:
            async with self._lock:
                future = self._inflight.pop(key, None)
                if future is not None and not future.done():
                    future.set_exception(exc)
            raise

        async with self._lock:
            self._entries[key] = CacheEntry(
                value=value,
                expires_at=monotonic() + self.ttl_seconds,
            )
            self._entries.move_to_end(key)
            self._evict_lru_locked()

            future = self._inflight.pop(key, None)
            if future is not None and not future.done():
                future.set_result(value)

        return value, "miss"


class RequestMetrics:
    def __init__(self, summary_every: int = 100) -> None:
        self.summary_every = summary_every
        self._lock = threading.Lock()
        self.total_requests = 0
        self.search_requests = 0
        self.error_requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_shared = 0
        self.total_latency_ms = 0.0
        self.max_latency_ms = 0.0

    def record(self, path: str, latency_ms: float, cache_status: str, status_code: int) -> None:
        with self._lock:
            self.total_requests += 1
            self.total_latency_ms += latency_ms
            self.max_latency_ms = max(self.max_latency_ms, latency_ms)

            if path.endswith("/search"):
                self.search_requests += 1
                if cache_status == "hit":
                    self.cache_hits += 1
                elif cache_status == "miss":
                    self.cache_misses += 1
                elif cache_status == "shared":
                    self.cache_shared += 1

            if status_code >= 500:
                self.error_requests += 1

            should_log_summary = self.total_requests % self.summary_every == 0
            snapshot = (
                self.total_requests,
                self.search_requests,
                self.cache_hits,
                self.cache_misses,
                self.cache_shared,
                self.error_requests,
                self.total_latency_ms / self.total_requests,
                self.max_latency_ms,
            )

        if should_log_summary:
            total_requests, search_requests, cache_hits, cache_misses, cache_shared, error_requests, avg_latency_ms, max_latency_ms = snapshot
            LOGGER.info(
                "metrics total_requests=%s search_requests=%s cache_hits=%s "
                "cache_misses=%s cache_shared=%s errors=%s avg_latency_ms=%.2f max_latency_ms=%.2f",
                total_requests,
                search_requests,
                cache_hits,
                cache_misses,
                cache_shared,
                error_requests,
                avg_latency_ms,
                max_latency_ms,
            )


class SearchService:
    def __init__(self) -> None:
        self.cache = LruTtlCache(CACHE_MAX_ENTRIES, CACHE_TTL_SECONDS)
        self.search_semaphore = asyncio.Semaphore(SEARCH_CONCURRENCY_LIMIT)
        self.refresh_lock = asyncio.Lock()
        self.last_db_check_at = 0.0
        self.db_mtime_ns = self._read_db_mtime()

    @staticmethod
    def _normalize_cache_key(query: str) -> str:
        return " ".join(query.lower().split())

    @staticmethod
    def _read_db_mtime() -> int | None:
        try:
            return DB_PATH.stat().st_mtime_ns
        except FileNotFoundError:
            return None

    async def warm(self) -> None:
        await run_in_threadpool(refresh_search_cache)
        self.db_mtime_ns = self._read_db_mtime()
        LOGGER.info("search runtime warmed")

    async def maybe_refresh_runtime(self) -> None:
        now = monotonic()
        if now - self.last_db_check_at < DB_REFRESH_CHECK_INTERVAL_SECONDS:
            return

        async with self.refresh_lock:
            now = monotonic()
            if now - self.last_db_check_at < DB_REFRESH_CHECK_INTERVAL_SECONDS:
                return

            self.last_db_check_at = now
            current_mtime_ns = self._read_db_mtime()
            if current_mtime_ns == self.db_mtime_ns:
                return

            await run_in_threadpool(refresh_search_cache)
            await self.cache.clear()
            self.db_mtime_ns = current_mtime_ns
            LOGGER.info("detected search DB update; refreshed runtime and cleared query cache")

    async def execute_search(self, query: str):
        cache_key = self._normalize_cache_key(query)

        async def loader():
            async with self.search_semaphore:
                return tuple(await run_in_threadpool(run_search, query))

        return await self.cache.get_or_load(cache_key, loader)


search_service = SearchService()
metrics = RequestMetrics()


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        await search_service.warm()
    except Exception:
        LOGGER.exception("failed to warm search runtime; continuing with lazy initialization")
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started_at = perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception:
        LOGGER.exception("request failed method=%s path=%s", request.method, request.url.path)
        raise
    finally:
        latency_ms = (perf_counter() - started_at) * 1000.0
        cache_status = getattr(request.state, "cache_status", "n/a")
        search_latency_ms = getattr(request.state, "search_latency_ms", None)
        result_total = getattr(request.state, "result_total", None)
        query = getattr(request.state, "query", "")
        truncated_query = query[:LOG_QUERY_MAX_LENGTH]

        metrics.record(request.url.path, latency_ms, cache_status, status_code)

        if search_latency_ms is None:
            LOGGER.info(
                "request method=%s path=%s status=%s latency_ms=%.2f",
                request.method,
                request.url.path,
                status_code,
                latency_ms,
            )
        else:
            LOGGER.info(
                "request method=%s path=%s status=%s latency_ms=%.2f search_ms=%.2f "
                "cache=%s total=%s q=%r",
                request.method,
                request.url.path,
                status_code,
                latency_ms,
                search_latency_ms,
                cache_status,
                result_total,
                truncated_query,
            )


@app.get("/")
async def root():
    return {"message": "API is running"}


async def search_response(
    request: Request,
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
):
    request.state.query = q

    await search_service.maybe_refresh_runtime()

    search_started_at = perf_counter()
    all_results, cache_status = await search_service.execute_search(q)
    request.state.search_latency_ms = (perf_counter() - search_started_at) * 1000.0
    request.state.cache_status = cache_status

    total = len(all_results)
    request.state.result_total = total

    start = (page - 1) * limit
    end = start + limit
    paginated = all_results[start:end]

    formatted = [
        {
            "title": result["title"],
            "url": result["url"],
            "score": result["score"],
            "snippet": result["snippet"],
        }
        for result in paginated
    ]

    return {"results": formatted, "total": total}


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "db_exists": DB_PATH.exists(),
    }


@app.get("/api/search")
async def api_search(
    request: Request,
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
):
    return await search_response(request=request, q=q, page=page, limit=limit)


@app.get("/search")
async def search_api(
    request: Request,
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
):
    return await search_response(request=request, q=q, page=page, limit=limit)
