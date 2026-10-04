# Checklist — Cierre del algoritmo de búsqueda (Bloque 4a)

Orden recomendado: de las piezas más aisladas (fáciles de probar solas) a la orquestación final.

## 1. `freshness/hash_utils.py`

- [x] Función que recibe dos hashes (o dos textos) y devuelve si coinciden.
- [x] Función que calcula el hash de un texto (mover aquí el `hashlib.sha256(...).hexdigest()` que ya tenías en el script de SearXNG).
- [x] Probarla suelta con dos textos iguales y dos distintos, sin nada más de por medio.

## 2. `freshness/freshness_checker.py`

- [ ] Función que, dada una página guardada (con su `etag` / `last_modified_header` / `content_hash` / `saved_at`), decide si sigue "fresca" o hay que refrescarla.
- [ ] Orden de prioridad a respetar: ETag (`If-None-Match`) → Last-Modified (`If-Modified-Since`) → hash manual (descarga completa + comparación) → ventana de tiempo (último recurso).
- [ ] Devuelve algo claro: por ejemplo `"fresh"` / `"stale"` / `"needs_refetch"` (o un booleano simple si os basta).
- [ ] Decidir y fijar el valor de la ventana de frescura (el "detalle pendiente" que dejasteis abierto hace tiempo) — aunque sea un número de partida a ajustar después.
- [ ] Probarla con una página simulada en cada uno de los 4 escenarios (con ETag, con Last-Modified, con solo hash, sin nada).

## 3. `ingestion/searxng_client.py`

- [ ] Mover aquí la parte de tu script actual que solo habla con SearXNG: la petición `requests.get(...)` + `response.raise_for_status()` + `response.json()`.
- [ ] Debe devolver únicamente la lista de resultados en bruto (`data["results"]`), sin tocar BBDD ni trafilatura.
- [ ] Nada de `print` dentro — eso es trabajo de quien la llame.

## 4. `ingestion/content_extractor.py`

- [ ] Mover aquí la parte de extracción: `trafilatura.fetch_url` + `trafilatura.extract`, con las comprobaciones de `None` que ya tenías.
- [ ] Usa `findPageByUrl` (de `repository/pages.py`) antes de extraer — si ya existe, no la vuelve a descargar.
- [ ] Usa `hash_utils.py` (punto 1) para calcular el hash, no lo recalcules aquí a mano.
- [ ] Al guardar, llama tanto a `insert_page` (si es nueva) como a `insert_searches` + el vínculo en `search_page` (esto último probablemente haya que añadirlo a `repository/searches.py` si aún no existe la función `link_search_to_page`).
- [ ] Debe devolver el `page_id` (nuevo o existente), no imprimir nada.

## 5. `repository/searches.py` — completar lo que falta

- [ ] Revisar que `insert_searches()` devuelve `search_id` (`cur.lastrowid`).
- [ ] Añadir `link_search_to_page(cur, search_id, page_id, result_position)` si no existe todavía — inserta en la tabla `search_page`.

## 6. `search/search_orchestrator.py` (la pieza nueva central)

- [ ] Recibe la consulta del usuario (ya stemizada o sin stemizar, decidir en qué punto se stemiza).
- [ ] Paso 1: llama a `local_search.py` para traer candidatos locales (FTS5 + bm25).
- [ ] Paso 2: para cada candidato, llama a `freshness_checker.py` — si está "stale", dispara el refresco de esa página concreta (reutilizando `content_extractor.py` sobre una URL ya conocida, no una búsqueda nueva).
- [ ] Paso 3: decide si los resultados locales (ya frescos) son **suficientes** — definir aquí el criterio concreto (por ejemplo: "si hay menos de N resultados locales válidos, ir a SearXNG" — fijar N).
- [ ] Paso 4: si no son suficientes, llama a `searxng_client.py`, y por cada resultado nuevo llama a `content_extractor.py`.
- [ ] Paso 5: llama a `insert_searches` (registra la búsqueda) y vincula cada página mostrada en `search_page` con su `result_position`.
- [ ] Paso 6: fusiona (local + nuevos de SearXNG) y devuelve la lista final ordenada — sin `print`, solo devuelve datos.

## 7. `main.py` — simplificar

- [ ] Quitar cualquier llamada directa a `repository/*` o `trafilatura` que haya quedado aquí.
- [ ] Solo debe: pedir `input()`, llamar a `search_orchestrator`, e imprimir el resultado que le devuelva.

## 8. Pruebas de integración, antes de dar el bloque por cerrado

- [ ] Buscar algo que YA está en local y fresco → comprobar que NO llama a SearXNG (verificable viendo que no hay tráfico de red, o con un log/print temporal de depuración).
- [ ] Buscar algo que está en local pero "viejo" (forzar manualmente una fecha antigua en `saved_at` para probarlo) → comprobar que SÍ refresca esa página.
- [ ] Buscar algo que no existe en absoluto en local → comprobar que va a SearXNG, guarda las páginas nuevas, y las vincula correctamente en `search_page`.
- [ ] Repetir la misma búsqueda una segunda vez → comprobar que la segunda vez ya no vuelve a traer todo de SearXNG (sale de local).

## 9. Documentación

- [ ] Actualizar `bitacora-bloque4a.md` con la Semana 3-4: diseño del orquestador, decisión de la ventana de frescura, resultados de las pruebas de integración del punto 8.
- [ ] Actualizar el README si la estructura de carpetas final difiere de lo ya documentado.
