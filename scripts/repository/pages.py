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



def get_page_state(cur, page_id):
    """Return the fields needed to decide whether a page changed, as a dict.

    Returns None if the page does not exist.
    """
    cur.execute(
        """SELECT id, title, extracted_content, content_hash, etag,
                  last_modified_header, state_content, last_verified_at
           FROM pages WHERE id = ?""",
        (page_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None

    # cur.description holds the column names of the last query,
    # so zipping names with values gives us a dict
    columns = [c[0] for c in cur.description]
    return dict(zip(columns, row))


def replace_content(cur, page_id, new_content, new_hash, etag, last_modified):
    """Replace a page's content and keep the FTS index in sync.

    It does not decide anything: it always replaces. It works for both
    snippet -> full content and old version -> new version, because the
    mechanics are identical.

    Does NOT commit: the caller owns the transaction.
    Returns False if the page does not exist, True otherwise.
    """
    # 1. Read the current text. We need the OLD content to remove it from
    #    the index, so this must happen before the UPDATE
    cur.execute(
        "SELECT title, extracted_content FROM pages WHERE id = ?", (page_id,)
    )
    row = cur.fetchone()
    if row is None:
        return False
    title, old_content = row

    # 2. Remove the old entry from pages_fts. pages_fts is an external-content
    #    FTS5 table (no triggers), so it must be told the EXACT stemmed values
    #    that were indexed. Run this exactly once per replacement.
    cur.execute(
        """INSERT INTO pages_fts(pages_fts, rowid, title, extracted_content)
           VALUES ('delete', ?, ?, ?)""",
        (page_id, stem_text(title), stem_text(old_content)),
    )

    # 3. Update the real row. Dates are stored in UTC (datetime('now')).
    #    Convert to local time only when displaying them.
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

    # 4. Index the new content, stemmed, with the same rowid as the page.
    #    Index and queries must always go through the same stemming.
    cur.execute(
        """INSERT INTO pages_fts(rowid, title, extracted_content)
           VALUES (?, ?, ?)""",
        (page_id, stem_text(title), stem_text(new_content)),
    )
    return True


def mark_verified(cur, page_id, etag=None, last_modified=None):
    """Record that the origin site was checked and the content is unchanged.

    Only touches dates and, if new headers arrive, updates them.
    COALESCE(?, column) keeps the stored header when the server did not
    send one this time, instead of overwriting it with NULL.

    Does NOT commit: the caller owns the transaction.
    """
    cur.execute(
        """UPDATE pages
           SET last_verified_at = datetime('now'),
               etag = COALESCE(?, etag),
               last_modified_header = COALESCE(?, last_modified_header)
           WHERE id = ?""",
        (etag, last_modified, page_id),
    )
          
          
def mark_not_found(cur, status_code, page_id):
    
    if status_code == 404 or status_code == 410: 
        
        cur.execute(
            
            """
            
            UPDATE pages 
            SET  original_disappear = 1
            WHERE id = ? 
            
            """, 
            (page_id,)
                
        )
        
        return 'gone'
    
    elif status_code == 200 or status_code == 304: 
        
        cur.execute(
            
            """
            
            UPDATE pages 
            SET  original_disappear = 0
            WHERE id = ? 
            
            """, 
            (page_id,)
             
        )
        return "exists"  
    
    else: 
        
        return "unknown" 
        
       

        
        
        
    

        