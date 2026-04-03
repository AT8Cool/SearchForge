import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

CREATE_DB_SCRIPT = ROOT / "app" / "models" / "create_db.py"
DEFAULT_CRAWLER_SCRIPT = ROOT / "crawler" / "crawler2.py"
BUILD_INDEX_SCRIPT = ROOT / "indexer" / "build_index.py"
LOAD_SQLITE_SCRIPT = ROOT / "app" / "models" / "json_to_sqlite.py"
PAGERANK_SCRIPT = ROOT / "app" / "core" / "pagerank.py"

CLEAN_PATHS = [
    DATA_DIR / "pages.json",
    DATA_DIR / "pages.jsonl",
    DATA_DIR / "index.json",
    DATA_DIR / "idf.json",
    DATA_DIR / "search.db",
    DATA_DIR / "failed_urls.log",
    DATA_DIR / "index_shards",
]


@dataclass(slots=True)
class StepResult:
    name: str
    elapsed_seconds: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the crawl -> index -> load -> pagerank pipeline."
    )
    parser.add_argument("--python", default=sys.executable, help="Python executable to use.")
    parser.add_argument(
        "--crawler-script",
        default=str(DEFAULT_CRAWLER_SCRIPT),
        help="Crawler entrypoint to run.",
    )
    parser.add_argument("--skip-clean", action="store_true")
    parser.add_argument("--skip-create-db", action="store_true")
    parser.add_argument("--skip-crawl", action="store_true")
    parser.add_argument("--skip-index", action="store_true")
    parser.add_argument("--skip-load", action="store_true")
    parser.add_argument("--skip-pagerank", action="store_true")

    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--crawler-workers", type=int)
    parser.add_argument("--max-per-domain", type=int)
    parser.add_argument("--crawler-batch-size", type=int)
    parser.add_argument("--crawler-timeout", type=float)
    parser.add_argument("--crawler-retries", type=int)
    parser.add_argument("--per-domain-delay", type=float)
    parser.add_argument("--per-domain-concurrency", type=int)
    parser.add_argument("--crawler-status-every", type=int)

    parser.add_argument("--index-workers", type=int)
    parser.add_argument("--index-chunk-size", type=int)
    parser.add_argument("--index-shards", type=int)
    parser.add_argument("--index-log-every", type=int)

    return parser.parse_args()


def remove_path(path: Path) -> None:
    if not path.exists():
        return

    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def clean_outputs() -> None:
    print("\n== Cleaning old pipeline artifacts ==")
    for path in CLEAN_PATHS:
        remove_path(path)
        print(f"Removed: {path.relative_to(ROOT)}")


def run_step(name: str, command: list[str]) -> StepResult:
    print(f"\n== Running: {name} ==")
    print("Command:", " ".join(command))
    started_at = perf_counter()

    completed = subprocess.run(command, cwd=ROOT)
    elapsed = perf_counter() - started_at

    if completed.returncode != 0:
        print(f"\nPipeline failed during: {name}")
        print(f"Exit code: {completed.returncode}")
        raise SystemExit(completed.returncode)

    print(f"Completed: {name} ({elapsed:.2f}s)")
    return StepResult(name=name, elapsed_seconds=elapsed)


def append_option(command: list[str], flag: str, value) -> None:
    if value is None:
        return
    command.extend([flag, str(value)])


def build_crawler_command(args: argparse.Namespace) -> list[str]:
    command = [args.python, args.crawler_script]
    append_option(command, "--max-pages", args.max_pages)
    append_option(command, "--max-workers", args.crawler_workers)
    append_option(command, "--max-per-domain", args.max_per_domain)
    append_option(command, "--batch-size", args.crawler_batch_size)
    append_option(command, "--timeout", args.crawler_timeout)
    append_option(command, "--max-retries", args.crawler_retries)
    append_option(command, "--per-domain-delay", args.per_domain_delay)
    append_option(command, "--per-domain-concurrency", args.per_domain_concurrency)
    append_option(command, "--status-every", args.crawler_status_every)
    return command


def build_index_command(args: argparse.Namespace) -> list[str]:
    command = [args.python, str(BUILD_INDEX_SCRIPT)]
    append_option(command, "--workers", args.index_workers)
    append_option(command, "--chunk-size", args.index_chunk_size)
    append_option(command, "--shards", args.index_shards)
    append_option(command, "--log-every", args.index_log_every)
    return command


def summarize(results: list[StepResult], total_elapsed_seconds: float) -> None:
    print("\n== Pipeline Summary ==")
    for result in results:
        print(f"{result.name}: {result.elapsed_seconds:.2f}s")
    print(f"Total: {total_elapsed_seconds:.2f}s")


def main() -> None:
    args = parse_args()
    started_at = perf_counter()
    results: list[StepResult] = []

    if not args.skip_clean:
        clean_outputs()

    if not args.skip_create_db:
        results.append(run_step("Create DB", [args.python, str(CREATE_DB_SCRIPT)]))

    if not args.skip_crawl:
        results.append(run_step("Crawler", build_crawler_command(args)))

    if not args.skip_index:
        results.append(run_step("Build Index", build_index_command(args)))

    if not args.skip_load:
        results.append(run_step("Load to SQLite", [args.python, str(LOAD_SQLITE_SCRIPT)]))

    if not args.skip_pagerank:
        results.append(run_step("PageRank", [args.python, str(PAGERANK_SCRIPT)]))

    total_elapsed_seconds = perf_counter() - started_at
    summarize(results, total_elapsed_seconds)
    print("\nPipeline completed successfully.")


if __name__ == "__main__":
    main()
