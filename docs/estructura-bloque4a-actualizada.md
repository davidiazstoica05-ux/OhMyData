# Estructura actualizada — conexión SearXNG ↔ BBDD (Bloque 4a, Semana 3-4)

```
scripts/
│
├── db/
│   └── connection.py               # ya existe: DB_PATH + get_connection()
│
├── repository/
│   ├── pages.py                    # ya existe: insert_page(), findPageByUrl()
│   └── searches.py                 # ya existe: insert_searches() — AHORA SÍ se usa
│                                    #   (falta añadir aquí: link_search_to_page(),
│                                    #   para la tabla search_page)
│
├── freshness/                      # NUEVA carpeta — todo lo de "¿sigue fresco esto?"
│   ├── hash_utils.py                # (1) comparación de hash — función aislada,
│   │                                 #     recibe dos valores, devuelve bool
│   └── freshness_checker.py         # (2) decide por PÁGINA individual:
│                                     #     ETag → Last-Modified → hash → ventana de tiempo,
│                                     #     en ese orden de prioridad
│
├── search/
│   ├── local_search.py             # ya existe: MATCH + bm25 sobre pages_fts
│   └── search_orchestrator.py      # NUEVA — (4) decide "¿local es suficiente, o
│                                     #     hace falta SearXNG?" — el corazón del flujo,
│                                     #     coordina local_search + ingestion + freshness
│
├── ingestion/                      # NUEVA carpeta — todo lo que trae contenido de fuera
│   ├── searxng_client.py            # (5) solo habla con SearXNG: petición + parseo JSON,
│   │                                 #     devuelve la lista de resultados en bruto
│   └── content_extractor.py         # (6) extrae y guarda UNA página: trafilatura,
│                                     #     calcula hash (usa hash_utils), findPageByUrl,
│                                     #     insert_page, insert_searches/link_search_to_page
│
├── steming.py                      # ya existe: tokenize(), stem_text(), prepare_fts_query()
│
├── testing/                        # ya existe: generate_test_data.py, queries-match.py, queries-like.py
│
└── main.py                         # interfaz fina: input() → search_orchestrator → mostrar resultado
                                     #   (SIN lógica de negocio, sin tocar BBDD directamente)
```

## Quién llama a quién (de arriba a abajo)

```
main.py
  └──> search_orchestrator.py                    (punto 7: el único orquestador)
         ├──> local_search.py                     (punto 3: busca en FTS5 primero)
         ├──> freshness_checker.py                (punto 2: por cada candidato local,
         │      └──> hash_utils.py                 ¿sigue fresco o hay que refrescar?)
         │
         └──> si no hay suficientes resultados locales frescos:
                ├──> searxng_client.py             (punto 5: trae resultados nuevos)
                └──> content_extractor.py          (punto 6: por cada resultado nuevo,
                       ├──> hash_utils.py            extrae + guarda si no existía)
                       ├──> repository/pages.py
                       └──> repository/searches.py
```

## Notas sobre la reorganización

- **`freshness/` es carpeta nueva** — separa toda la lógica de "¿esto sigue válido?" (ETag, Last-Modified, hash, ventana de tiempo) del resto, porque es una responsabilidad propia y bien delimitada que antes estaba mezclada dentro del mismo bucle que hacía de todo.
- **`ingestion/` es carpeta nueva** — agrupa todo lo que trae datos de fuera (SearXNG + extracción web), separado de `repository/` (que solo habla con la BBDD) y de `freshness/` (que solo decide si algo está desactualizado).
- **`search_orchestrator.py` es el único archivo que conoce y coordina todas las piezas** — es la pieza que faltaba (punto 4 de la lista anterior) y es la que convierte este diseño en algo coherente en vez de un único método gigante.
- **`main.py` ya no llama directamente a `insert_page` ni a ningún `repository/*`** — solo conoce `search_orchestrator`, manteniendo la regla de interfaz fina que ya teníais establecida desde el Bloque 2.
- El código que ya tienes escrito (la función `search_searxng` con trafilatura, hash, etc.) se reparte entre `ingestion/searxng_client.py` (la parte de la petición HTTP) e `ingestion/content_extractor.py` (la parte de trafilatura + hash + guardado) — no se tira nada, se separa.
