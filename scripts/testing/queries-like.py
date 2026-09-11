"""
Runs the same 5 logical queries using LIKE (sequential scan).
"""

import time

from db.conection import get_connection

def benchmark_query(cur, sql, params=(), repeats=200):
    cur.execute(sql, params).fetchall()  # Warm-up

    start = time.perf_counter()
    for _ in range(repeats):
        cur.execute(sql, params).fetchall()
    end = time.perf_counter()

    return (end - start) / repeats * 1000

def test_query(cur, label, sql, params=()):
    print(f"\n{label}")
    print(f"SQL: {sql}")

    results = cur.execute(sql, params).fetchall()
    time_ms = benchmark_query(cur, sql, params)

    print(f"-> Results returned: {len(results)}")
    print(f"-> Execution time:   {time_ms:.4f} ms")
    print("-" * 50)

def main():
    con = get_connection()
    cur = con.cursor()

    print("Starting LIKE test battery (average of 200 iterations)...")

    # 1. Search with many results
    test_query(cur,
        "1. Search with many results",
        "SELECT rowid, title FROM pages WHERE extracted_content LIKE '%privacidad%'")

    # 2. Search with few results
    test_query(cur,
        "2. Search with few results",
        "SELECT rowid, title FROM pages WHERE extracted_content LIKE '%xilofonomarcador%'")

    # 3. Equivalent to BM25 (search only, LIKE cannot rank by relevance)
    test_query(cur,
        "3. Equivalent to ranking (bulk search with no mathematical ordering)",
        "SELECT rowid, title FROM pages WHERE extracted_content LIKE '%datos%'")

    # 4. Exact phrase search (matches your dataset's plural form)
    test_query(cur,
        "4. Exact phrase search (Phrase Query)",
        "SELECT rowid, title FROM pages WHERE extracted_content LIKE '%motores de búsqueda%'")

    # 5. Search with boolean operators (shows how inefficient LIKE is here)
    test_query(cur,
        "5. Search with boolean operators (AND, OR)",
        """SELECT rowid, title FROM pages
           WHERE extracted_content LIKE '%privacidad%'
           AND (extracted_content LIKE '%datos%' OR extracted_content LIKE '%publicidad%')""")

    con.close()

if __name__ == "__main__":
    main()