
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from db.connection import get_connection

from steming import stem_text
import freshness.hash_utils



def replace_content(cur, page_id, new_content, new_hash, etag, last_modified):
    cur.execute(
        "SELECT title, extracted_content, content_hash, etag FROM pages WHERE id = ?",
        (page_id,),
    )
    row = cur.fetchone()
    if row is None:
        return "not_found"
    title, old_content, old_hash, old_etag = row

    if etag is not None and etag == old_etag:
        cur.execute(
            "UPDATE pages SET last_verified_at = datetime('now') WHERE id = ?",
            (page_id,),
        )
        return "unchanged"


    if old_hash is not None and old_hash == new_hash:
        cur.execute(
            """UPDATE pages
               SET etag = ?, last_modified_header = ?,
                   last_verified_at = datetime('now')
               WHERE id = ?""",
            (etag, last_modified, page_id),
        )
        return "unchanged"

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
    return "replaced"

#Test zone 
# ---------------- Test zone ----------------



@contextmanager
def transaction():
    """Conexión real, pero todo lo que se haga dentro se deshace al salir."""
    con = get_connection()
    try:
        yield con, con.cursor()
    finally:
        con.rollback()      # no se guarda nada en tu base
        con.close()


def h(text):
    # el hash siempre sobre el texto stemizado, como en el proyecto
    return freshness.hash_utils.create_hash(freshness.hash_utils.steming_text(text))


def make_page(cur, content, content_hash, etag, state):
    """Crea una página de prueba (URL única) y la indexa. Devuelve su id."""
    cur.execute(
        """INSERT INTO pages (url, title, extracted_content, content_hash,
                              etag, state_content, original_disappear)
           VALUES (?, ?, ?, ?, ?, ?, 0)""",
        (f"https://test.example/{uuid.uuid4().hex}", "Titulo", content,
         content_hash, etag, state),
    )
    page_id = cur.lastrowid
    cur.execute(
        "INSERT INTO pages_fts(rowid, title, extracted_content) VALUES (?, ?, ?)",
        (page_id, stem_text("Titulo"), stem_text(content)),
    )
    return page_id


def found(cur, word, page_id):
    """¿Encuentra el índice esta página buscando esta palabra?"""
    cur.execute(
        "SELECT rowid FROM pages_fts WHERE pages_fts MATCH ?", (stem_text(word),)
    )
    ids = [r[0] for r in cur.fetchall()]
    return ids.count(page_id)       # 0 = no aparece, 1 = bien, 2 = duplicada


def get_page(cur, page_id):
    cur.execute(
        """SELECT extracted_content, content_hash, state_content, etag,
                  last_modified_header, last_verified_at
           FROM pages WHERE id = ?""",
        (page_id,),
    )
    return cur.fetchone()


def test_not_found():
    with transaction() as (con, cur):
        assert replace_content(cur, 99999999, "x", h("x"), None, None) == "not_found"


def test_snippet_becomes_full():
    with transaction() as (con, cur):
        pid = make_page(cur, "snippet viejo quirunculo", None, None, "Snippet")
        texto = "texto completo zampabollos"

        res = replace_content(cur, pid, texto, h(texto), '"e1"', "lm1")
        content, hash_, state, etag, lm, verified = get_page(cur, pid)

        assert res == "replaced"
        assert content == texto
        assert hash_ == h(texto)
        assert state == "Full"
        assert etag == '"e1"' and lm == "lm1"
        assert verified is not None
        assert found(cur, "quirunculo", pid) == 0     # lo viejo ya no se encuentra
        assert found(cur, "zampabollos", pid) == 1    # lo nuevo, una sola vez


def test_same_etag_is_unchanged():
    with transaction() as (con, cur):
        orig = "contenido original quirunculo"
        pid = make_page(cur, orig, h(orig), '"e1"', "Full")
        otro = "otro texto distinto"

        res = replace_content(cur, pid, otro, h(otro), '"e1"', None)

        assert res == "unchanged"
        assert get_page(cur, pid)[0] == orig            # no se tocó el contenido
        assert get_page(cur, pid)[5] is not None        # pero se marcó verificada
        assert found(cur, "quirunculo", pid) == 1


def test_same_hash_new_etag_updates_headers_only():
    with transaction() as (con, cur):
        orig = "contenido original quirunculo"
        pid = make_page(cur, orig, h(orig), '"e1"', "Full")
        mismo = "Contenido   ORIGINAL, quirunculo!"     # otro formato, mismo hash

        res = replace_content(cur, pid, mismo, h(mismo), '"e2"', "lm2")
        content, _, _, etag, lm, _ = get_page(cur, pid)

        assert res == "unchanged"
        assert content == orig
        assert etag == '"e2"' and lm == "lm2"


def test_changed_content_replaces():
    with transaction() as (con, cur):
        orig = "contenido original quirunculo"
        pid = make_page(cur, orig, h(orig), '"e1"', "Full")
        nuevo = "contenido nuevo zampabollos"

        res = replace_content(cur, pid, nuevo, h(nuevo), '"e2"', None)

        assert res == "replaced"
        assert get_page(cur, pid)[0] == nuevo
        assert found(cur, "quirunculo", pid) == 0
        assert found(cur, "zampabollos", pid) == 1


def test_second_call_is_unchanged():
    with transaction() as (con, cur):
        orig = "contenido original quirunculo"
        pid = make_page(cur, orig, h(orig), '"e1"', "Full")
        nuevo = "contenido nuevo zampabollos"
        args = (pid, nuevo, h(nuevo), '"e2"', None)

        assert replace_content(cur, *args) == "replaced"
        assert replace_content(cur, *args) == "unchanged"
        assert found(cur, "zampabollos", pid) == 1     # sin duplicados en el índice


if __name__ == "__main__":
    tests = [
        test_not_found,
        test_snippet_becomes_full,
        test_same_etag_is_unchanged,
        test_same_hash_new_etag_updates_headers_only,
        test_changed_content_replaces,
        test_second_call_is_unchanged,
    ]
    for t in tests:
        try:
            t()
            print(f"OK    {t.__name__}")
        except AssertionError as e:
            print(f"FALLA {t.__name__}: {e!r}")
