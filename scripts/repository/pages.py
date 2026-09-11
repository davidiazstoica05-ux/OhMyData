import sys
from pathlib import Path

# Makes sure the 'scripts/' folder is always on sys.path, regardless of
# whether this file is imported via main.py or run/imported from
# somewhere else (e.g. scripts/testing/). Without this, "from steming
# import stem_text" only works if the process happened to be launched
# from inside scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from steming import stem_text


def insert_page(cur, url, title, content, content_hash):
    """Inserts a page into 'pages' (original, readable text) and mirrors
    a STEMMED version of title/content into 'pages_fts' (no triggers, so
    this has to be done manually, using the same rowid).

    The FTS5 index only ever stores stemmed roots — never raw text —
    so it must be searched using queries stemmed the same way
    (see prepare_fts_query in steming.py, used by search/local_search.py).
    """
    cur.execute(
        """INSERT INTO pages (url, title, extracted_content, content_hash)
           VALUES (?, ?, ?, ?)""",
        (url, title, content, content_hash),
    )
    page_id = cur.lastrowid

    stemmed_title = stem_text(title)
    stemmed_content = stem_text(content)

    cur.execute(
        """INSERT INTO pages_fts (rowid, title, extracted_content)
           VALUES (?, ?, ?)""",
        (page_id, stemmed_title, stemmed_content),
    )
    return page_id


def findPageByUrl(cur, url):
    """Returns the rowid of a page in 'pages' by its URL, or None if not found."""
    cur.execute("SELECT rowid FROM pages WHERE url = ?", (url,))
    result = cur.fetchone()
    return result[0] if result else None