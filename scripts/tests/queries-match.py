"""
Runs the 5 key FTS5 queries for the logbook, measuring the average
response time and showing the actual result count.
"""

import sqlite3
import time
from pathlib import Path

# Same path as in generate_test_data.py
DB_PATH = Path(__file__).resolve().parent.parent / "db" / "MyData.db"

def benchmark_query(cur, sql, params=(), repeats=200):
    # Warm-up to load into SQLite's cache
    cur.execute(sql, params).fetchall()

    start = time.perf_counter()
    for _ in range(repeats):
        cur.execute(sql, params).fetchall()
    end = time.perf_counter()

    return (end - start) / repeats * 1000  # milliseconds

def test_query(cur, label, sql):
    print(f"\n{label}")
    print(f"SQL: {sql}")

    # Get the actual results
    results = cur.execute(sql).fetchall()

    # Measure timing
    time_ms = benchmark_query(cur, sql)

    print(f"-> Results returned: {len(results)}")
    print(f"-> Execution time:   {time_ms:.4f} ms")

    # Show a sample if there are results, to check the BM25 ranking
    if results:
        print(f"-> Sample (Top 2): {results[:2]}")
    print("-" * 50)

def main():
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()

        print("Starting FTS5 test battery (average of 200 iterations)...")

        # 1. Search with many results
        test_query(cur,
            "1. Search with many results",
            "SELECT rowid, title FROM pages_fts WHERE pages_fts MATCH 'privacidad'")

        # 2. Search with few results (using 'xilofonomarcador', our unique term)
        test_query(cur,
            "2. Search with few results",
            "SELECT rowid, title FROM pages_fts WHERE pages_fts MATCH 'xilofonomarcador'")

        # 3. BM25 ranking in action
        test_query(cur,
            "3. BM25 ranking (ordered by relevance)",
            "SELECT rowid, title, rank FROM pages_fts WHERE pages_fts MATCH 'datos' ORDER BY rank")

        # 4. Exact phrase search
        test_query(cur,
            "4. Exact phrase search (Phrase Query)",
            "SELECT rowid, title FROM pages_fts WHERE pages_fts MATCH '\"motor de búsqueda\"'")

        # 5. Search with boolean operators
        test_query(cur,
            "5. Search with boolean operators (AND, OR)",
            "SELECT rowid, title FROM pages_fts WHERE pages_fts MATCH 'privacidad AND (datos OR publicidad)'")

    except sqlite3.OperationalError as e:
        print(f"Error: Could not connect to the database or the table is missing. Details: {e}")
    finally:
        if 'con' in locals():
            con.close()

if __name__ == "__main__":
    main()