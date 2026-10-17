import sys
from pathlib import Path

# Makes sure the 'scripts/' folder is always on sys.path, regardless of
# whether this file is imported via main.py or run/imported from
# somewhere else (e.g. scripts/testing/). Without this, "from steming
# import stem_text" only works if the process happened to be launched
# from inside scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from steming import stem_text
from freshness.hash_utils import compare_hashes

#Recordar que la tabla ha cambiado y ha crecido, por lo que hay que cambiar esta parte 
def insert_page(cur, url, title, extracted_content, content_hash, etag, state_content, original_disappear, last_modified_header):
    """Inserts a page into 'pages' (original, readable text) and mirrors
    a STEMMED version of title/content into 'pages_fts' (no triggers, so
    this has to be done manually, using the same rowid).

    The FTS5 index only ever stores stemmed roots — never raw text —
    so it must be searched using queries stemmed the same way
    (see prepare_fts_query in stemizador.py / main.py).
    """
    cur.execute(
        """INSERT INTO pages (url, title, extracted_content, content_hash , etag, state_content, original_disappear)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (url, title, extracted_content, content_hash, etag, state_content, original_disappear),
    )
    page_id = cur.lastrowid

    stemmed_title = stem_text(title)
    stemmed_content = stem_text(extracted_content)

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






def replace_content(cur, page_id, new_content, new_hash, etag=None, last_modified=None):

    cur.execute(
        "SELECT title, extracted_content FROM pages WHERE id = ?",
        (page_id,),
    )
    row = cur.fetchone()
    if row is None:
        return False                     
    title, old_content = row

    cur.execute(
        """INSERT INTO pages_fts(pages_fts, rowid, title, extracted_content)
           VALUES ('delete', ?, ?, ?)""",
        (page_id, stem_text(title), stem_text(old_content)),
    )

    cur.execute(
        """UPDATE pages
           SET extracted_content = ?,
               content_hash = ?,
               state_content = 'Full',
               etag = ?,
               last_modified_header = ?,
               last_changed_at = datetime('now'),
               last_verified_at = datetime('now')
           WHERE id = ?""",
        (new_content, new_hash, etag, last_modified, page_id),
    )

    cur.execute(
        """INSERT INTO pages_fts(rowid, title, extracted_content)
           VALUES (?, ?, ?)""",
        (page_id, stem_text(title), stem_text(new_content)),
    )
    return True
          
          
    
    

        