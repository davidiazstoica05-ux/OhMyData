# Checklist — Conexión SearXNG ↔ BBDD (Bloque 4a, cierre)

## Regla de diseño que guía todo este checklist

> **La Cajita solo contacta con una web de origen cuando el usuario elige esa página.**

- **Buscar** nunca toca webs de origen: o se resuelve en local, o se habla solo con los tres motores vía SearXNG.
- **Abrir** una página es el único momento en que se descarga (si es nueva) o se revalida (si ya estaba guardada).
- La pre-descarga del resto de resultados en una cola diferida queda **fuera del MVP**, como hito de la propuesta a NLnet.

Orden de trabajo recomendado: esquema y repositorio primero (desbloquean todo lo demás), luego las piezas aisladas, y la orquestación al final.

---

## 1. `freshness/hash_utils.py` ✅

- [x] Función que compara dos hashes y devuelve si coinciden.
- [x] Función que calcula el hash de un texto.
- [x] Probada suelta con textos iguales, distintos y con espacios extra.
- [ ] Pendiente menor: que `compare_hashes` devuelva `True`/`False` en vez de imprimir, y las pruebas dentro de `if __name__ == "__main__":`.

## 2. Esquema de la BBDD (`db/schema.sql`) — NUEVO, hacerlo antes que el resto

- [x] Añadir a `pages` las columnas `etag` y `last_modified_header` (cabeceras que manda la web original; pueden quedar vacías).
- [x] Añadir `last_verified_at`: cuándo se comprobó por última vez con la web original. Es distinta de `last_changed_at` (cuándo se detectó un cambio).
- [x] Añadir una columna de estado del contenido: solo snippet o contenido completo.
- [x]Añadir una marca de "original desaparecido", para cuando la web devuelva 404 o 410.
- [x] Recrear la BBDD de pruebas desde el esquema nuevo (lo más limpio con datos de prueba).

## 3. `repository/pages.py` — ampliar

- [ ] Guardar una página **solo con snippet** (título, URL, snippet de SearXNG), stemizando el snippet para `pages_fts`. Usa `findPageByUrl` para no duplicar.
- [ ] `insert_page` acepta y guarda las cabeceras nuevas.
- [ ] Función para **sustituir el contenido** de una página ya existente (snippet → completo, o versión vieja → nueva). Trampa clave: antes de sobrescribir, borrar la entrada de `pages_fts` pasando **exactamente los valores stemizados que se indexaron** (recalculados con `stem_text` sobre el texto viejo), y luego insertar los nuevos. Nunca usar el comando `rebuild` de FTS5.
- [ ] Función para marcar una página como verificada (solo actualiza `last_verified_at`).
- [ ] Función para marcar una página como "original desaparecido", sin borrar la copia.

## 4. `repository/searches.py` — completar

- [ ] `insert_searches` devuelve el `search_id`.
- [ ] Añadir la función que vincula búsqueda y página en `search_page`, con `result_position`.

## 5. `ingestion/searxng_client.py`

- [ ] Mover aquí solo la parte que habla con SearXNG: petición, comprobación de estado y parseo del JSON.
- [ ] Devuelve la lista de resultados en bruto. Sin BBDD, sin trafilatura y sin `print`.

## 6. `ingestion/content_extractor.py` — solo se llama al ABRIR una página

- [ ] Descargar con `requests` (no con `trafilatura.fetch_url`) para poder leer las cabeceras `ETag` y `Last-Modified`.
- [ ] Peticiones sueltas, **sin `Session`**, para que no se acumulen cookies entre descargas.
- [ ] Fijar un timeout y decidir qué User-Agent usar (el de `requests` por defecto se bloquea a menudo).
- [ ] Extraer el texto con `trafilatura.extract` sobre el HTML descargado, con comprobación de `None`.
- [ ] Calcular el hash del texto stemizado con `hash_utils`.
- [ ] Devolver texto, hash y cabeceras. El guardado lo coordina el orquestador a través del repositorio.

## 7. `freshness/freshness_checker.py` — CAMBIA: ya no se llama al buscar, solo al abrir una página guardada

Lo que ya hayas empezado sobre el orden ETag → Last-Modified → hash sigue valiendo. Cambian cuándo se llama y qué hace con cada resultado.

- [ ] **Paso 0 (nuevo)**: si `last_verified_at` es más reciente que la ventana de frescura, servir la copia local **sin contactar la web**. Así la ventana pasa de último recurso a primer filtro, y reduce los contactos.
- [ ] Fijar el valor de esa ventana (aunque sea provisional).
- [ ] Si hay que revalidar: `If-None-Match` si hay ETag; si no, `If-Modified-Since` si hay Last-Modified; si no, descarga completa y comparación de hash.
- [ ] Según la respuesta:
  - [ ] 304 → solo actualizar `last_verified_at`.
  - [ ] 200 → sustituir contenido, hash, cabeceras, `last_changed_at` y `last_verified_at` (con la función del punto 3).
  - [ ] 404 o 410 → conservar la copia y marcar "original desaparecido".
  - [ ] Otros errores (403, 429, timeout) → servir la copia local y no reintentar en bucle.
- [ ] Devolver un resultado claro (fresca / cambiada / desaparecida / error), sin imprimir.

## 8. `search/search_orchestrator.py` — dos operaciones separadas

**Buscar** (nunca toca webs de origen):

- [ ] Búsqueda local con `local_search.py`.
- [ ] Fijar el criterio de "resultados locales suficientes" (por ejemplo, un mínimo N).
- [ ] Si no son suficientes: `searxng_client`, y por cada resultado guardar la página solo con snippet (si no existía).
- [ ] Registrar la búsqueda y vincular cada página mostrada en `search_page`.
- [ ] Devolver la lista fusionada, indicando de cada resultado si es snippet o completo y cuándo se verificó.

**Abrir** (el único punto que contacta webs de origen):

- [ ] Si la página es solo snippet → `content_extractor` y sustituir por el contenido completo.
- [ ] Si ya era completa → `freshness_checker`.
- [ ] Devolver el contenido a mostrar.

## 9. `main.py`

- [ ] Mostrar los resultados numerados.
- [ ] Dejar elegir un número para abrir esa página y mostrar su contenido.
- [ ] Solo `input()`, llamadas al orquestador y mostrar. Sin lógica de negocio.

## 10. Pruebas de integración

- [ ] **Buscar no contacta ninguna web de origen** (verificable con un registro temporal en `content_extractor` y `freshness_checker`).
- [ ] Abrir una página solo-snippet la descarga una vez y pasa a completa.
- [ ] Volver a abrirla dentro de la ventana no contacta la web.
- [ ] Abrirla fuera de la ventana revalida (forzando a mano una `last_verified_at` antigua): probar el caso 304 y el 200.
- [ ] Una página guardada cuyo original da 404 se sigue mostrando, marcada como desaparecida.
- [ ] Repetir la misma búsqueda sale de local, sin ir a SearXNG.

## 11. Documentación

- [ ] Bitácora del Bloque 4a: evolución del diseño. Detectamos que la descarga en bloque reproducía la página de resultados y facilitaba correlaciones por hora, y adoptamos la regla de contactar solo lo que el usuario elige.
- [ ] Añadir a `trabajo-pendiente-post-mvp.md` y al boceto de propuesta el hito **"pre-descarga diferida y descorrelacionada"**: cola persistente, trabajador en segundo plano, retrasos aleatorios, orden barajado y revalidación en segundo plano.
- [ ] Hablar con Antonio de en qué red Docker vive el componente que descarga páginas (necesita salida a internet y acceso a la BBDD).
