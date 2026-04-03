from __future__ import annotations

import os
import shutil
import sys
import urllib.request
from pathlib import Path


def main() -> int:
    db_path = Path(os.getenv("SEARCH_DB_PATH", "data/search.db")).expanduser()

    if db_path.exists():
        print(f"Search database found at {db_path}")
        return 0

    db_url = os.getenv("SEARCH_DB_URL", "").strip()
    if not db_url:
        print(
            "Search database not found and SEARCH_DB_URL is not set. "
            "Provide SEARCH_DB_URL or include the database file in the deployment.",
            file=sys.stderr,
        )
        return 1

    db_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading search database to {db_path}...")

    try:
        with urllib.request.urlopen(db_url) as response, db_path.open("wb") as target:
            shutil.copyfileobj(response, target)
    except Exception:
        if db_path.exists():
            db_path.unlink()
        raise

    print("Search database download complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
