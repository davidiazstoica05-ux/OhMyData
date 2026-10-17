
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from db.connection import get_connection

from steming import stem_text
import freshness.hash_utils


def replace_content(cur, page_id, new_content, new_hash, etag=None, last_modified=None):

    cur.execute(
        "SELECT title, extracted_content FROM pages WHERE id = ?",
        (page_id,),
    )
    
    #Desde la consulta cojo la fila y la convierto en una tupla
    row = cur.fetchone()
    if row is None:
        return False                     
    title, old_content = row

    #La uso aqui
    cur.execute(
        """INSERT INTO pages_fts(pages_fts, rowid, title, extracted_content)
           VALUES ('delete', ?, ?, ?)""",
        (page_id, stem_text(title), stem_text(old_content)),
    )

    cur.execute(
        """UPDATE pages
           SET extracted_content = ?,
               content_hash = ?,
               state_content = 'FULL',
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


#Test zone 

if __name__ == "__main__":
    con = get_connection()
    cur = con.cursor()

    text = "OhMyData!"                                  
    new_hash = freshness.hash_utils.create_hash(
        freshness.hash_utils.steming_text(text)        
    )

    ok = replace_content(cur, 1, text, new_hash, None, None)
    con.commit()                                        

    print("Reemplazada:", ok)

    cur.execute(
        "SELECT extracted_content, content_hash, state_content, last_verified_at "
        "FROM pages WHERE id = 1"
    )
    print(cur.fetchone())

    con.close()

