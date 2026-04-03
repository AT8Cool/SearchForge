from array import array
from itertools import islice
import sqlite3

import numpy as np
from scipy.sparse import csr_matrix

from app.core.settings import get_db_path

DB = get_db_path()

DAMPING = 0.85
MAX_ITERATIONS = 100
TOLERANCE = 1e-8
UPDATE_BATCH_SIZE = 5000


def configure_connection(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute("PRAGMA cache_size = -200000")
    conn.execute("PRAGMA mmap_size = 268435456")


def batched(iterable, size: int):
    iterator = iter(iterable)
    while True:
        batch = list(islice(iterator, size))
        if not batch:
            break
        yield batch


def load_page_ids(conn: sqlite3.Connection) -> list[int]:
    return [row[0] for row in conn.execute("SELECT id FROM pages ORDER BY id")]


def build_index_lookup(page_ids: list[int]) -> tuple[bool, dict[int, int]]:
    is_dense = all(page_id == index for index, page_id in enumerate(page_ids))
    if is_dense:
        return True, {}
    return False, {page_id: index for index, page_id in enumerate(page_ids)}


def load_graph(
    conn: sqlite3.Connection,
    page_count: int,
    dense_ids: bool,
    page_id_to_index: dict[int, int],
) -> tuple[csr_matrix, np.ndarray]:
    src_indices_buffer = array("I")
    dst_indices_buffer = array("I")

    if dense_ids:
        for from_page, to_page in conn.execute("SELECT from_page, to_page FROM links"):
            if 0 <= from_page < page_count and 0 <= to_page < page_count:
                src_indices_buffer.append(from_page)
                dst_indices_buffer.append(to_page)
    else:
        lookup = page_id_to_index.get
        for from_page, to_page in conn.execute("SELECT from_page, to_page FROM links"):
            src_index = lookup(from_page)
            if src_index is None:
                continue

            dst_index = lookup(to_page)
            if dst_index is None:
                continue

            src_indices_buffer.append(src_index)
            dst_indices_buffer.append(dst_index)

    if not src_indices_buffer:
        empty_matrix = csr_matrix((page_count, page_count), dtype=np.float64)
        return empty_matrix, np.zeros(page_count, dtype=np.int32)

    src_indices = np.frombuffer(src_indices_buffer, dtype=np.uint32).astype(np.int32, copy=False)
    dst_indices = np.frombuffer(dst_indices_buffer, dtype=np.uint32).astype(np.int32, copy=False)

    out_degree = np.bincount(src_indices, minlength=page_count).astype(np.int32, copy=False)
    edge_weights = 1.0 / out_degree[src_indices]

    # Build a CSR matrix of inbound transition weights: matrix[dst, src] = 1 / out_degree[src]
    transition = csr_matrix(
        (edge_weights, (dst_indices, src_indices)),
        shape=(page_count, page_count),
        dtype=np.float64,
    )

    return transition, out_degree


def compute_pagerank(
    transition: csr_matrix,
    out_degree: np.ndarray,
    page_count: int,
) -> tuple[np.ndarray, int, float]:
    if page_count == 0:
        return np.array([], dtype=np.float64), 0, 0.0

    pagerank = np.full(page_count, 1.0 / page_count, dtype=np.float64)
    teleport = np.full(page_count, (1.0 - DAMPING) / page_count, dtype=np.float64)
    dangling_mask = out_degree == 0

    last_delta = 0.0
    for iteration in range(1, MAX_ITERATIONS + 1):
        dangling_mass = pagerank[dangling_mask].sum()
        new_pagerank = teleport + DAMPING * transition.dot(pagerank)
        new_pagerank += DAMPING * dangling_mass / page_count

        delta = np.abs(new_pagerank - pagerank).sum()
        print(f"Iteration {iteration}: delta={delta:.12f}")

        pagerank = new_pagerank
        last_delta = delta

        if delta <= TOLERANCE:
            print(f"Converged after {iteration} iterations.")
            break
    else:
        iteration = MAX_ITERATIONS
        print(f"Reached max iterations ({MAX_ITERATIONS}) with delta={last_delta:.12f}.")

    max_pr = float(pagerank.max()) if page_count else 1.0
    if max_pr > 0.0:
        pagerank /= max_pr

    return pagerank, iteration, last_delta


def store_pagerank(
    conn: sqlite3.Connection,
    page_ids: list[int],
    pagerank: np.ndarray,
) -> None:
    updates = zip(pagerank.tolist(), page_ids)

    with conn:
        for batch in batched(updates, UPDATE_BATCH_SIZE):
            conn.executemany(
                "UPDATE pages SET pagerank=? WHERE id=?",
                batch,
            )


def main() -> None:
    conn = sqlite3.connect(DB)
    configure_connection(conn)

    try:
        page_ids = load_page_ids(conn)
        page_count = len(page_ids)

        if page_count == 0:
            print("No pages found.")
            return

        print(f"Pages: {page_count}")

        dense_ids, page_id_to_index = build_index_lookup(page_ids)
        transition, out_degree = load_graph(
            conn=conn,
            page_count=page_count,
            dense_ids=dense_ids,
            page_id_to_index=page_id_to_index,
        )

        print(
            f"Graph loaded: edges={transition.nnz}, "
            f"dangling_nodes={(out_degree == 0).sum()}, dense_ids={dense_ids}"
        )

        pagerank, iterations, delta = compute_pagerank(
            transition=transition,
            out_degree=out_degree,
            page_count=page_count,
        )

        store_pagerank(conn, page_ids, pagerank)
        print(
            f"PageRank computed and stored. iterations={iterations} "
            f"final_delta={delta:.12f}"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
