import argparse
import asyncio
import json
import random
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse, urlunparse

import aiohttp
from bs4 import BeautifulSoup

# ================= CONFIG =================
MAX_PAGES = 10000
MAX_WORKERS = 150
MAX_PER_DOMAIN = 50
BATCH_SIZE = 500
REQUEST_TIMEOUT = 10.0
MAX_RETRIES = 2
PER_DOMAIN_DELAY = 0.25
PER_DOMAIN_CONCURRENCY = 2

OUTPUT_FILE = Path("data/pages.jsonl")
FAILED_LOG = Path("data/failed_urls.log")

USER_AGENT = (
    "SearchEngineCrawler/2.0 (+https://example.com/bot) "
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

# ================= SEEDS =================
SEED_URLS = [
    "https://en.wikipedia.org/wiki/Computer_science",
    "https://en.wikipedia.org/wiki/Mathematics",
    "https://en.wikipedia.org/wiki/Database",
    "https://en.wikipedia.org/wiki/Artificial_intelligence",
    "https://en.wikipedia.org/wiki/Computer_Network",
    "https://en.wikipedia.org/wiki/Operating_system",
    "https://en.wikipedia.org/wiki/Programming_language",
    "https://en.wikipedia.org/wiki/Theory_of_computation",
    "https://en.wikipedia.org/wiki/Programming_paradigm",
    "https://en.wikipedia.org/wiki/Data_structure",
    "https://en.wikipedia.org/wiki/",
    "https://medlineplus.gov/healthtopics.html",
    "https://www.nasa.gov/",
    "https://developer.mozilla.org/en-US/docs/Web",
    "https://cs50.harvard.edu/x/",
    "https://www.britannica.com/",
    "https://www.theverge.com/tech",
    "https://www.investopedia.com/",
    "https://stackoverflow.com/questions",
]

# ================= FILTERS =================
ALLOWED_DOMAINS = [
    "wikipedia.org",
    "developer.mozilla.org",
    "docs.python.org",
    "nodejs.org",
    "rust-lang.org",
    "nextjs.org",
    "react.dev",
    "freecodecamp.org",
    "w3schools.com",
    "geeksforgeeks.org",
    "programiz.com",
    "tutorialspoint.com",
    "cs50.harvard.edu",
    "khanacademy.org",
    "nationalgeographic.com",
    "sciencedaily.com",
    "livescience.com",
    "britannica.com",
    "nasa.gov",
    "esa.int",
    "scientificamerican.com",
    "ocw.mit.edu",
    "medlineplus.gov",
    "cdc.gov",
    "who.int",
    "genome.gov",
    "ncbi.nlm.nih.gov",
    "nature.com",
    "science.org",
    "openstax.org",
    "ck12.org",
    "pll.harvard.edu",
    "theverge.com",
    "investopedia.com",
    "stackoverflow.com",
    "myanimelist.net",
    "animenewsnetwork.com",
    "ign.com",
    "gamespot.com",
]

BAD_PATTERNS = [
    "privacy",
    "terms",
    "login",
    "signup",
    "account",
    "policy",
    "cdn-cgi",
    "profile",
    "comment",
    "tag",
    "author",
    "video",
    "gallery",
    "share",
    "print",
    "download",
    "register",
    "advert",
    "ads",
    "?utm_",
    "&utm_",
    "episode",
    "season",
    "watch",
    "review",
    "trailer",
    "characters",
    "cast",
    "staff",
    "forum",
    "user",
    "topic",
    "news",
]


def canonicalize(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower().replace("www.", ""),
            parsed.path.rstrip("/"),
            "",
            "",
            "",
        )
    )


def is_allowed(url: str) -> bool:
    domain = urlparse(url).netloc
    if "wikipedia.org" in domain:
        return "en.wikipedia.org" in domain
    return any(domain.endswith(item) for item in ALLOWED_DOMAINS)


def is_valid(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and "." in parsed.netloc
    except Exception:
        return False


def detect_source(url: str) -> str:
    domain = urlparse(url).netloc

    if "wikipedia" in domain:
        return "wikipedia"
    if "developer.mozilla" in domain:
        return "mdn"
    if "docs.python" in domain:
        return "docs"
    if "stackoverflow" in domain:
        return "qa"
    if "investopedia" in domain:
        return "finance"
    if "theverge" in domain:
        return "news"
    if "nasa" in domain:
        return "science"
    if "medlineplus" in domain:
        return "health"
    if "britannica" in domain:
        return "encyclopedia"
    return "other"


def parse_page(soup: BeautifulSoup) -> tuple[str | None, str | None]:
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    paragraphs = soup.find_all("p")[:10]
    text = " ".join(p.get_text(" ", strip=True) for p in paragraphs)

    if len(text) < 100:
        return None, None

    return title, text


def parse_document(url: str, html: str) -> tuple[dict | None, list[str], str | None]:
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        return None, [], "parse_error"

    title, text = parse_page(soup)
    if not title or not text:
        return None, [], "skip"

    discovered_links: list[str] = []
    seen_links: set[str] = set()

    for tag in soup.find_all("a", href=True):
        href = tag["href"]

        if any(item in href for item in ("javascript:", "mailto:", "#")):
            continue

        abs_url = canonicalize(urljoin(url, href))

        if any(item in abs_url for item in ("myanimelist", "ign", "gamespot")):
            if abs_url.count("/") > 5:
                continue

        if not is_valid(abs_url):
            continue

        if any(pattern in abs_url for pattern in BAD_PATTERNS):
            continue

        if not is_allowed(abs_url):
            continue

        if abs_url in seen_links:
            continue

        seen_links.add(abs_url)
        discovered_links.append(abs_url)

        if len(discovered_links) >= 25:
            break

    record = {
        "url": url,
        "title": title,
        "text": text,
        "source": detect_source(url),
        "links": discovered_links,
    }
    return record, discovered_links, None


def append_lines(path: Path, lines: list[str]) -> None:
    if not lines:
        return

    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


@dataclass(slots=True)
class CrawlConfig:
    max_pages: int = MAX_PAGES
    max_workers: int = MAX_WORKERS
    max_per_domain: int = MAX_PER_DOMAIN
    batch_size: int = BATCH_SIZE
    timeout: float = REQUEST_TIMEOUT
    max_retries: int = MAX_RETRIES
    per_domain_delay: float = PER_DOMAIN_DELAY
    per_domain_concurrency: int = PER_DOMAIN_CONCURRENCY
    output_file: Path = OUTPUT_FILE
    failed_log: Path = FAILED_LOG
    status_every: int = 250


@dataclass(slots=True)
class CrawlStats:
    scheduled: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    http_error: int = 0
    timeout: int = 0
    parse_fail: int = 0
    retries: int = 0
    discovered: int = 0
    started_at: float = field(default_factory=time.perf_counter)


@dataclass(slots=True)
class DomainState:
    semaphore: asyncio.Semaphore
    lock: asyncio.Lock
    next_available_at: float = 0.0


class DomainRateLimiter:
    def __init__(self, delay: float, concurrency: int) -> None:
        self.delay = delay
        self.concurrency = max(1, concurrency)
        self._domains: dict[str, DomainState] = {}
        self._domains_lock = asyncio.Lock()

    async def _state_for(self, domain: str) -> DomainState:
        async with self._domains_lock:
            if domain not in self._domains:
                self._domains[domain] = DomainState(
                    semaphore=asyncio.Semaphore(self.concurrency),
                    lock=asyncio.Lock(),
                )
            return self._domains[domain]

    @asynccontextmanager
    async def throttle(self, domain: str):
        state = await self._state_for(domain)
        await state.semaphore.acquire()

        try:
            async with state.lock:
                now = asyncio.get_running_loop().time()
                wait_for = state.next_available_at - now
                if wait_for > 0:
                    await asyncio.sleep(wait_for)
                    now = asyncio.get_running_loop().time()
                state.next_available_at = now + self.delay
            yield
        finally:
            state.semaphore.release()


class AsyncCrawler:
    def __init__(self, config: CrawlConfig) -> None:
        self.config = config
        self.frontier: asyncio.Queue[str | None] = asyncio.Queue()
        self.writer_queue: asyncio.Queue[tuple[str, dict | str] | None] = asyncio.Queue()
        self.stats = CrawlStats()
        self.rate_limiter = DomainRateLimiter(
            delay=config.per_domain_delay,
            concurrency=config.per_domain_concurrency,
        )
        self.seen_urls: set[str] = set()
        self.domain_count: defaultdict[str, int] = defaultdict(int)
        self.state_lock = asyncio.Lock()
        self.session: aiohttp.ClientSession | None = None

    async def run(self, seeds: Iterable[str]) -> None:
        self._prepare_output()

        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        connector = aiohttp.TCPConnector(
            limit=self.config.max_workers,
            limit_per_host=0,
            ttl_dns_cache=300,
            enable_cleanup_closed=True,
        )

        async with aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={"User-Agent": USER_AGENT},
            raise_for_status=False,
        ) as session:
            self.session = session

            writer_task = asyncio.create_task(self.writer())
            worker_tasks = [
                asyncio.create_task(self.worker(worker_id))
                for worker_id in range(self.config.max_workers)
            ]

            await self.schedule_urls(seeds)
            await self.frontier.join()

            for _ in worker_tasks:
                self.frontier.put_nowait(None)
            await asyncio.gather(*worker_tasks)

            self.writer_queue.put_nowait(None)
            await self.writer_queue.join()
            await writer_task

        self.print_stats()

    def _prepare_output(self) -> None:
        self.config.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.config.failed_log.parent.mkdir(parents=True, exist_ok=True)

        for path in (self.config.output_file, self.config.failed_log):
            if path.exists():
                path.unlink()

    async def schedule_urls(self, urls: Iterable[str]) -> int:
        staged: list[str] = []
        scheduled_now = 0

        async with self.state_lock:
            for raw_url in urls:
                if self.stats.scheduled >= self.config.max_pages:
                    break

                normalized = canonicalize(raw_url)
                if not is_valid(normalized):
                    continue
                if not is_allowed(normalized):
                    continue
                if normalized in self.seen_urls:
                    continue

                domain = urlparse(normalized).netloc
                if self.domain_count[domain] >= self.config.max_per_domain:
                    continue

                self.seen_urls.add(normalized)
                self.domain_count[domain] += 1
                self.stats.scheduled += 1
                staged.append(normalized)
                scheduled_now += 1

        for url in staged:
            self.frontier.put_nowait(url)

        return scheduled_now

    async def fetch(self, url: str) -> str | None:
        if self.session is None:
            raise RuntimeError("Client session was not initialized.")

        domain = urlparse(url).netloc

        for attempt in range(self.config.max_retries + 1):
            try:
                async with self.rate_limiter.throttle(domain):
                    async with self.session.get(url) as response:
                        if response.status != 200:
                            self.stats.http_error += 1
                            if response.status in {429, 500, 502, 503, 504} and attempt < self.config.max_retries:
                                self.stats.retries += 1
                                await asyncio.sleep(self.retry_delay(attempt, response))
                                continue

                            self.stats.failed += 1
                            self.writer_queue.put_nowait(("failed", url))
                            return None

                        content_type = response.headers.get("Content-Type", "").lower()
                        if "text/html" not in content_type:
                            self.stats.failed += 1
                            return None

                        return await response.text(errors="ignore")

            except asyncio.TimeoutError:
                self.stats.timeout += 1
                if attempt < self.config.max_retries:
                    self.stats.retries += 1
                    await asyncio.sleep(self.retry_delay(attempt))
                    continue

                self.stats.failed += 1
                self.writer_queue.put_nowait(("failed", url))
                return None

            except aiohttp.ClientError:
                if attempt < self.config.max_retries:
                    self.stats.retries += 1
                    await asyncio.sleep(self.retry_delay(attempt))
                    continue

                self.stats.failed += 1
                self.writer_queue.put_nowait(("failed", url))
                return None

        self.stats.failed += 1
        self.writer_queue.put_nowait(("failed", url))
        return None

    def retry_delay(self, attempt: int, response: aiohttp.ClientResponse | None = None) -> float:
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    return max(0.0, float(retry_after))
                except ValueError:
                    pass

        base = 0.5 * (2 ** attempt)
        return base + random.uniform(0.0, 0.3)

    async def worker(self, worker_id: int) -> None:
        while True:
            url = await self.frontier.get()
            try:
                if url is None:
                    return

                html = await self.fetch(url)
                if not html:
                    continue

                record, links, parse_error = await asyncio.to_thread(parse_document, url, html)

                if parse_error == "parse_error":
                    self.stats.parse_fail += 1
                    self.stats.failed += 1
                    self.writer_queue.put_nowait(("failed", url))
                    continue

                if parse_error == "skip" or record is None:
                    self.stats.parse_fail += 1
                    self.stats.skipped += 1
                    continue

                self.writer_queue.put_nowait(("page", record))
                self.stats.success += 1

                new_links = await self.schedule_urls(links)
                self.stats.discovered += new_links

                if self.config.status_every and self.stats.success % self.config.status_every == 0:
                    elapsed = max(time.perf_counter() - self.stats.started_at, 0.001)
                    rate = self.stats.success / elapsed
                    print(
                        f"[{self.stats.success}] {url} | "
                        f"scheduled={self.stats.scheduled} queue={self.frontier.qsize()} "
                        f"rate={rate:.2f}/s"
                    )

            except Exception as exc:
                self.stats.failed += 1
                self.writer_queue.put_nowait(("failed", f"{url}\t{type(exc).__name__}"))
            finally:
                self.frontier.task_done()

    async def writer(self) -> None:
        page_buffer: list[str] = []
        failed_buffer: list[str] = []

        while True:
            item = await self.writer_queue.get()
            try:
                if item is None:
                    break

                kind, payload = item
                if kind == "page":
                    page_buffer.append(json.dumps(payload, ensure_ascii=False))
                    if len(page_buffer) >= self.config.batch_size:
                        await asyncio.to_thread(
                            append_lines,
                            self.config.output_file,
                            page_buffer.copy(),
                        )
                        page_buffer.clear()
                else:
                    failed_buffer.append(str(payload))
                    if len(failed_buffer) >= 100:
                        await asyncio.to_thread(
                            append_lines,
                            self.config.failed_log,
                            failed_buffer.copy(),
                        )
                        failed_buffer.clear()
            finally:
                self.writer_queue.task_done()

        if page_buffer:
            await asyncio.to_thread(
                append_lines,
                self.config.output_file,
                page_buffer.copy(),
            )

        if failed_buffer:
            await asyncio.to_thread(
                append_lines,
                self.config.failed_log,
                failed_buffer.copy(),
            )

    def print_stats(self) -> None:
        elapsed = max(time.perf_counter() - self.stats.started_at, 0.001)

        print("\n==== CRAWL STATS ====")
        print(f"Scheduled:  {self.stats.scheduled}")
        print(f"Success:    {self.stats.success}")
        print(f"Failed:     {self.stats.failed}")
        print(f"Skipped:    {self.stats.skipped}")
        print(f"HTTP Err:   {self.stats.http_error}")
        print(f"Timeouts:   {self.stats.timeout}")
        print(f"ParseFail:  {self.stats.parse_fail}")
        print(f"Retries:    {self.stats.retries}")
        print(f"Discovered: {self.stats.discovered}")
        print(f"Elapsed:    {elapsed:.2f}s")
        print(f"Throughput: {self.stats.success / elapsed:.2f} pages/sec")


def parse_args() -> CrawlConfig:
    parser = argparse.ArgumentParser(
        description="High-performance async crawler with domain-aware rate limiting."
    )
    parser.add_argument("--max-pages", type=int, default=MAX_PAGES)
    parser.add_argument("--max-workers", type=int, default=MAX_WORKERS)
    parser.add_argument("--max-per-domain", type=int, default=MAX_PER_DOMAIN)
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--timeout", type=float, default=REQUEST_TIMEOUT)
    parser.add_argument("--max-retries", type=int, default=MAX_RETRIES)
    parser.add_argument("--per-domain-delay", type=float, default=PER_DOMAIN_DELAY)
    parser.add_argument("--per-domain-concurrency", type=int, default=PER_DOMAIN_CONCURRENCY)
    parser.add_argument("--status-every", type=int, default=250)
    parser.add_argument("--output", type=Path, default=OUTPUT_FILE)
    parser.add_argument("--failed-log", type=Path, default=FAILED_LOG)
    args = parser.parse_args()

    return CrawlConfig(
        max_pages=args.max_pages,
        max_workers=args.max_workers,
        max_per_domain=args.max_per_domain,
        batch_size=args.batch_size,
        timeout=args.timeout,
        max_retries=args.max_retries,
        per_domain_delay=args.per_domain_delay,
        per_domain_concurrency=args.per_domain_concurrency,
        output_file=args.output,
        failed_log=args.failed_log,
        status_every=args.status_every,
    )


async def main() -> None:
    config = parse_args()
    crawler = AsyncCrawler(config)
    await crawler.run(SEED_URLS)


if __name__ == "__main__":
    asyncio.run(main())
