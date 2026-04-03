import os
from pathlib import Path


DEFAULT_DB_PATH = Path("data/search.db")


def get_db_path() -> Path:
    configured_path = os.getenv("SEARCH_DB_PATH", "").strip()
    if configured_path:
        return Path(configured_path).expanduser()

    return DEFAULT_DB_PATH
