"""
Generates filler data in the database and compares the query time of
MATCH (FTS5) vs LIKE (sequential scan) at a larger scale.

Every insert now goes through the stemmer (stemizador.py) before being
written to 'pages_fts', so that search queries processed with the same
stemmer (via prepare_fts_query, used in main.py) can correctly match
different word forms sharing the same root (e.g. "gestionar" / "gestión").
The original, readable text is still stored as-is in 'pages'.

Includes a "needle in a haystack" test: a single page containing a unique
word that appears nowhere else in the dataset, to show FTS5's real
advantage on selective terms (as opposed to common terms that appear
in a large fraction of rows, where the advantage is much smaller).

Also includes two stemming test pages ("gestionar" / "gestión"), each
using only one of the two word forms, to verify that the stemmer
correctly links different forms of the same root when searching.

Note: this file is for seeding the local test dataset only. A separate
file will handle stemming content ingested from SearXNG once that
integration exists (Bloque 4).

Usage:
    python3 generate_test_data.py
"""

import random
import time

from db.conection import get_connection
from steming import stem_text

NUM_ROWS = 50000

# Content kept in Spanish so it matches the terms used in queries-match.py /
# queries-like.py (e.g. "privacidad", "datos").
# Note: with 2-4 topics picked out of 15 per row, every topic ends up
# appearing in a fairly large fraction of rows (~15-27%).
TOPICS = [
    "La privacidad digital es un derecho fundamental en la sociedad actual.",
    "Muchos usuarios ignoran cuántos datos personales comparten cada día.",
    "Los motores de búsqueda tradicionales guardan historial para publicidad.",
    "Una base de datos local evita que terceros accedan a tu información.",
    "El código abierto permite auditar cómo se gestionan realmente los datos.",
    "Correr de forma regular mejora la salud cardiovascular a largo plazo.",
    "Programar en Python es accesible incluso para principiantes absolutos.",
    "Docker facilita el despliegue de aplicaciones sin depender del host.",
    "Un modelo de lenguaje pequeño puede ejecutarse en hardware modesto.",
    "La gestión eficiente de proyectos requiere priorizar bien las tareas.",
    "El fútbol despierta pasiones que van mucho más allá del partido en sí.",
    "La historia de la informática está llena de avances inesperados.",
    "Un índice invertido permite encontrar texto de forma casi instantánea.",
    "Una red privada virtual cifra el tráfico entre dos dispositivos remotos.",
    "El excedente de datos capturados rara vez beneficia al usuario original.",
]

FILLER = [
    "Este es un párrafo extra generado solo para aumentar el volumen de prueba.",
    "El contenido de esta página es ficticio y se usa solo para medir tiempos.",
    "Se añade texto adicional sin relación directa con el tema principal.",
    "Esta frase no aporta información relevante, solo ocupa espacio en el índice.",
]

# Unique word that appears nowhere else in the dataset
NEEDLE_TERM = "xilofonomarcador"


def generate_content():
    sentences = random.sample(TOPICS, k=random.randint(2, 4))
    sentences += random.sample(FILLER, k=random.randint(1, 2))
    random.shuffle(sentences)
    return " ".join(sentences)


def insert_page(cur, url, title, content, content_hash):
    """Inserts a page into 'pages' (original, readable text) and mirrors
    a STEMMED version of title/content into 'pages_fts' (no triggers, so
    this has to be done manually, using the same rowid).

    The FTS5 index only ever stores stemmed roots — never raw text —
    so it must be searched using queries stemmed the same way
    (see prepare_fts_query in stemizador.py / main.py).
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


def benchmark_query(cur, sql, params, repeats=200):
    # Warm-up: run once without measuring, so SQLite can cache what it needs.
    cur.execute(sql, params).fetchall()

    start = time.perf_counter()
    for _ in range(repeats):
        cur.execute(sql, params).fetchall()
    end = time.perf_counter()

    return (end - start) / repeats * 1000  # average ms per execution


def run_comparison(cur, term, total_rows, label):
    # NOTE: term must already be stemmed when calling this for pages_fts
    # comparisons, since the index only contains stemmed roots. LIKE still
    # searches the raw text in 'pages', so it needs the literal word form.
    match_sql = "SELECT title FROM pages_fts WHERE pages_fts MATCH ?"
    like_sql = "SELECT title FROM pages WHERE extracted_content LIKE ?"

    like_params = (f"%{term}%",)
    match_params = (term,)

    # Run once (untimed) to get the actual result counts.
    match_results = cur.execute(match_sql, match_params).fetchall()
    like_results = cur.execute(like_sql, like_params).fetchall()

    match_avg_ms = benchmark_query(cur, match_sql, match_params)
    like_avg_ms = benchmark_query(cur, like_sql, like_params)

    print(f"--- {label}: '{term}' over ~{total_rows} rows (avg of 200 runs) ---")
    print(f"MATCH (FTS5): {len(match_results)} results, {match_avg_ms:.4f} ms avg")
    print(f"LIKE:         {len(like_results)} results, {like_avg_ms:.4f} ms avg")

    if len(match_results) != len(like_results):
        print("⚠️  Warning: MATCH and LIKE returned a different number of "
              "results. This comparison may not be meaningful — check that "
              "pages_fts is being populated correctly before trusting the "
              "speed factor.")

    if like_avg_ms > 0:
        factor = like_avg_ms / max(match_avg_ms, 1e-9)
        print(f"FTS5 was approximately {factor:.1f}x faster than LIKE.\n")


def main():
    con = get_connection()
    cur = con.cursor()

    print(f"Inserting {NUM_ROWS} filler rows (content stemmed before indexing)...")
    insert_start = time.perf_counter()

    for i in range(NUM_ROWS):
        insert_page(
            cur,
            url=f"https://filler.example.com/page-{i}",
            title=f"Filler page {i}",
            content=generate_content(),
            content_hash=f"fillerhash{i}",
        )

    # Insert the "needle" page: a unique term that appears nowhere else.
    insert_page(
        cur,
        url="https://filler.example.com/needle",
        title="Needle page",
        content=f"Esta única página contiene la palabra {NEEDLE_TERM} para pruebas.",
        content_hash="needlehash",
    )

    # Insert the two stemming test pages: each uses only one of the two
    # word forms ("gestionar" / "gestión"), so a search that finds both
    # confirms the stemmer is correctly linking the shared root.
    insert_page(
        cur,
        url="https://ejemplo.com/prueba-gestionar",
        title="Cómo gestionar un proyecto pequeño",
        content="Gestionar un proyecto con pocos recursos exige priorizar bien las tareas desde el principio.",
        content_hash="stemtest-gestionar",
    )
    insert_page(
        cur,
        url="https://ejemplo.com/prueba-gestion",
        title="La importancia de la buena gestión",
        content="Una buena gestión del tiempo evita que el equipo se disperse en detalles poco importantes.",
        content_hash="stemtest-gestion",
    )

    con.commit()
    insert_end = time.perf_counter()
    total_rows = NUM_ROWS + 3
    print(f"Insertion completed in {insert_end - insert_start:.3f} seconds.\n")

    # --- Comparison 1: common term (already stemmed: "privacidad" -> "privacid") ---
    run_comparison(cur, stem_text("privacidad"), total_rows, "Common term")

    # --- Comparison 2: needle in a haystack (stemmed too, for consistency) ---
    run_comparison(cur, stem_text(NEEDLE_TERM), total_rows, "Unique term")

    con.close()


if __name__ == "__main__":
    main()