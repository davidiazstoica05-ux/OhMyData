import sqlite3
import time
from pathlib import Path

from steming import prepare_fts_query

DB_PATH = Path(__file__).resolve().parent.parent / "db" / "MyData.db"


def benchmark_query(cur, sql, params=(), repeats=50):
    """Runs the query once (untimed) plus a small number of timed repeats,
    since interactive queries don't need the same statistical rigor as
    the benchmark scripts."""
    cur.execute(sql, params).fetchall()  # warm-up

    start = time.perf_counter()
    for _ in range(repeats):
        cur.execute(sql, params).fetchall()
    end = time.perf_counter()

    return (end - start) / repeats * 1000  # ms


def search(cur, user_query: str):
    # The search term must go through the same stemming process as the
    # stored content, or the roots won't match (see stemizador.py).
    fts_query = prepare_fts_query(user_query)

    if not fts_query:
        print("The query didn't produce any valid search term after processing.")
        return

    sql = """
        SELECT rowid, title, bm25(pages_fts) AS relevance
        FROM pages_fts
        WHERE pages_fts MATCH ?
        ORDER BY relevance
    """

    results = cur.execute(sql, (fts_query,)).fetchall()
    time_ms = benchmark_query(cur, sql, (fts_query,))

    print(f"\nOriginal query: {user_query}")
    print(f"Processed for FTS5: {fts_query}")
    print(f"-> Results found: {len(results)}")
    print(f"-> Average time: {time_ms:.4f} ms")

    if results:
        print("\nTop results (most relevant first):")
        for rowid, title, relevance in results[:10]:
            print(f"  [{relevance:.3f}] {title} (rowid={rowid})")
    print("-" * 50)


def main():
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()

        print("La Cajita — interactive local search (type 'exit' to quit)")
        print("-" * 50)

        while True:
            user_query = input("\nSearch query: ").strip()

            if user_query.lower() in ("exit", "quit", "salir"):
                break

            if not user_query:
                continue

            search(cur, user_query)

    except sqlite3.OperationalError as e:
        print(f"Error: Could not connect to the database or the table is missing. Details: {e}")
    finally:
        if 'con' in locals():
            con.close()


if __name__ == "__main__":
    main()