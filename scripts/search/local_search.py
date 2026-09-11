import sys
from pathlib import Path

# See pages.py for why this is here: guarantees 'scripts/' is on sys.path
# regardless of how/where this module ends up being imported from.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from steming import prepare_fts_query


def search(cur, user_query: str):
    # The search term must go through the same stemming process as the
    # stored content, or the roots won't match (see steming.py).
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

    print(f"\nOriginal query: {user_query}")
    print(f"Processed for FTS5: {fts_query}")
    print(f"-> Results found: {len(results)}")

    if results:
        print("\nTop results (most relevant first):")
        for rowid, title, relevance in results[:10]:
            print(f"  [{relevance:.3f}] {title} (rowid={rowid})")
    print("-" * 50)