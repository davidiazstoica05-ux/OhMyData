"""
Generates filler data in the database and compares the query time of
MATCH (FTS5) vs LIKE (sequential scan) at a larger scale.

Includes a "needle in a haystack" test: a single page containing a unique
word that appears nowhere else in the dataset, to show FTS5's real
advantage on selective terms (as opposed to common terms that appear
in a large fraction of rows, where the advantage is much smaller).

Note: there are no triggers on the 'pages' table, so every insert must
be mirrored manually into 'pages_fts' using the same rowid.

Usage:
    python3 generate_test_data.py
"""

import sqlite3
import random
import time
from pathlib import Path

# Resolves relative to this file's location, so it works
# regardless of the directory you run the script from.
DB_PATH = Path(__file__).resolve().parent.parent / "db" / "MyData.db"
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
    """Inserts a page into both 'pages' and 'pages_fts' (no triggers, so
    the FTS5 mirror has to be done manually, using the same rowid)."""
    cur.execute(
        """INSERT INTO pages (url, title, extracted_content, content_hash)
           VALUES (?, ?, ?, ?)""",
        (url, title, content, content_hash),
    )
    page_id = cur.lastrowid
    cur.execute(
        """INSERT INTO pages_fts (rowid, title, extracted_content)
           VALUES (?, ?, ?)""",
        (page_id, title, content),
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
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    print(f"Inserting {NUM_ROWS} filler rows...")
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

    con.commit()
    insert_end = time.perf_counter()
    total_rows = NUM_ROWS + 1
    print(f"Insertion completed in {insert_end - insert_start:.3f} seconds.\n")

    # --- Comparison 1: common term ---
    run_comparison(cur, "privacidad", total_rows, "Common term")

    # --- Comparison 2: needle in a haystack ---
    run_comparison(cur, NEEDLE_TERM, total_rows, "Unique term")

    con.close()


if __name__ == "__main__":
    main()