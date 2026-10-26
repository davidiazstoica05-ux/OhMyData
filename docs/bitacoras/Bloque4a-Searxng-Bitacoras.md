## Punto 1 — `freshness/hash_utils.py`: detectar si el contenido ha cambiado

### Qué hace

Tres funciones pequeñas, todas puras (no tocan la BBDD):

- `create_hash(text)`: devuelve el SHA-256 del texto en hexadecimal.
- `compare_hashes(local_hash, remote_hash)`: compara dos hashes con `hmac.compare_digest` y devuelve `True`/`False`.
- `steming_text(text)`: envoltorio sobre `stem_text` de `steming.py`, para que quien calcule un hash tenga siempre el texto ya normalizado a mano.

### Decisiones tomadas

- **El hash se calcula sobre el texto stemizado, no sobre el original.** Surgió al probar qué pasaba con dobles espacios: con el texto crudo, una página que solo cambia de formato (espacios, saltos de línea, mayúsculas, signos de puntuación) daría un hash distinto y se contaría como "cambiada". Sobre el texto stemizado, todo eso desaparece.
- **Coste aceptado:** un cambio puramente morfológico ("gestión" → "gestionar") se reduce a la misma raíz y no se detecta como cambio. Se considera irrelevante para el caso de uso (memoria personal de páginas).
- **Una página solo-snippet no tiene hash** (`content_hash = NULL`): el snippet que devuelve SearXNG cambia de un motor a otro y de una consulta a otra, y eso no es un cambio de la página. El hash solo existe cuando hay contenido completo descargado.
- **`compare_hashes` devuelve un booleano en vez de imprimir.** La primera versión mostraba "same / not same" por pantalla; una función que decide debe devolver el resultado y que sea quien la llama quien lo muestre (si no, no se puede usar en un `if` ni probar con `assert`).

### Problemas encontrados

- **`ModuleNotFoundError` al importar `steming`** desde `freshness/`. Python solo busca módulos en la carpeta desde la que se lanza el script, no en `scripts/`. Solución: añadir `scripts/` al `sys.path` al principio del fichero con `Path(__file__).resolve().parent.parent`, el mismo patrón que ya se usa en `repository/`.

### Verificación

Pruebas en `scripts/testing/pruebas_hash.py`: textos iguales (mismo hash), textos distintos (hash distinto) y mismo texto con espacios de más (mismo hash tras stemizar).

---

## Punto 2 — Esquema de la BBDD: columnas nuevas en `pages`

### Qué se ha añadido

Cinco columnas nuevas en `pages` (`db/queries/CreateTables.sql`):

| Columna | Para qué sirve |
|---|---|
| `etag` | Cabecera `ETag` que manda la web original; se devuelve en `If-None-Match` al revalidar. Puede ser `NULL`. |
| `last_modified_header` | Cabecera `Last-Modified`; se devuelve en `If-Modified-Since`. Puede ser `NULL`. |
| `last_verified_at` | Última vez que se comprobó la página contra la web original. |
| `state_content` | Qué hay en `extracted_content`: `'Snippet'` (solo el extracto de SearXNG) o `'Full'` (texto completo descargado). |
| `original_disappear` | Marca 0/1: la web devolvió 404 o 410, pero se conserva la copia (caché anti-404). |

### Decisiones tomadas

- **`last_verified_at` y `last_changed_at` son cosas distintas.** `last_changed_at` es cuándo se detectó un cambio real; `last_verified_at` es cuándo se comprobó, haya cambiado o no. La ventana de frescura se calcula sobre la segunda.
- **`last_verified_at` no tiene `DEFAULT`.** Es deliberado: `NULL` significa "nunca verificada", que es el estado correcto de una página que solo tiene snippet. Con un valor por defecto de "ahora", todas las páginas nuevas parecerían recién verificadas y nunca se contactaría la web.
- **Todas las fechas se guardan en UTC** (`CURRENT_TIMESTAMP` / `datetime('now')`). Al ver una hora dos horas por detrás de la local (12:30 frente a 14:30) se comprobó que es el comportamiento documentado de SQLite. Se mantiene UTC en la base porque la ventana de frescura es una resta entre fechas y no se puede mezclar referencias; la conversión a hora local se hará solo al mostrar.
- **El estado del contenido usa siempre la misma escritura** (`'Snippet'` / `'Full'`). SQLite distingue mayúsculas al comparar cadenas, así que `'Full'` y `'FULL'` no coinciden y el error pasa en silencio.
- **`id INTEGER PRIMARY KEY` sin `AUTOINCREMENT`.** Declarada con exactamente ese tipo, la columna es un alias del `rowid` de SQLite y se asigna sola (máximo + 1). Ese mismo `rowid` se reutiliza al insertar en `pages_fts`.

### Problemas encontrados al recrear la BBDD de pruebas

- **`FileNotFoundError`** al leer el esquema: la ruta apuntaba a un archivo que no existía con ese nombre. El esquema vive en `db/queries/CreateTables.sql`.
- **Recrear no es solo `DROP TABLE pages`.** Hay que borrar también `search_page`, `pages_fts` y `searches`, y en el orden correcto (primero la tabla que depende de las otras), o `pages_fts` queda con raíces apuntando a filas inexistentes.
- **`sqlite3.ProgrammingError: Incorrect number of bindings`**: el `INSERT` de `insert_page` seguía con 4 columnas mientras se le pasaban 7 valores. La firma de la función y la sentencia SQL se actualizaron por separado.
- **`TypeError: unexpected keyword argument 'content'`**: al renombrar el parámetro a `extracted_content` se olvidó actualizar la llamada. Lección: el mismo dato tenía nombres distintos en el esquema, la función y la llamada.
- **Error de lógica en los datos de prueba:** `original_disappear = 0 if is_full else 1` marcaba como "desaparecidas" todas las páginas solo-snippet, que nunca han contactado la web. La marca solo tiene sentido en páginas completas.

### Datos de prueba

`generate_test_data.py` (ahora en `scripts/testing/generateDataSet/`) genera 50.000 páginas de relleno mezclando estados con `i % 2` (mitad `'Full'`, mitad `'Snippet'`): determinista, así que un fallo se puede repetir idéntico. Las páginas `'Snippet'` llevan `etag = NULL` y `content_hash = NULL`.

### Pendiente / punto a revisar

- `last_modified_header` está declarada como `DATETIME`, pero la cabecera `Last-Modified` es un texto tipo `Wed, 21 Oct 2015 07:28:00 GMT` y hay que devolverla tal cual en `If-Modified-Since`. Conviene declararla `TEXT` (implica recrear la BBDD de pruebas).

---

## Punto 3 — `repository/pages.py`: guardar, sustituir y verificar páginas

### Qué hay

| Función | Qué hace |
|---|---|
| `insert_page` | Inserta una página en `pages` y refleja su versión stemizada en `pages_fts` con el mismo `rowid`. |
| `findPageByUrl` | Devuelve el `rowid` de una página por su URL, o `None`. Evita duplicados. |
| `get_page_state` | Devuelve los campos que necesita quien decide (contenido, hash, ETag, estado, fechas) como diccionario, o `None`. |
| `replace_content` | Sustituye el contenido de una página y mantiene el índice FTS5 coherente. |
| `mark_verified` | Anota que la web se comprobó y el contenido sigue igual. |

Y en `freshness/freshness_checker.py`: `is_unchanged(stored, remote_etag, new_hash)`.

### Decisiones tomadas

- **Se separa decidir de modificar.** La primera versión de `replace_content` mezclaba las dos cosas (miraba el ETag y el hash y además escribía). Se dividió en: `is_unchanged` (decide, no escribe), `replace_content` (siempre sustituye) y `mark_verified` (solo anota la verificación). Así cada función hace una sola cosa y se puede probar sin las demás.
- **No se divide por snippet / versión nueva.** Mecánicamente, sustituir un snippet por el texto completo y una versión vieja por una nueva es lo mismo (borrar entrada del índice, actualizar, reindexar). La única diferencia es que el snippet no tiene hash, y eso ya lo resuelve `is_unchanged` (un hash `None` nunca coincide).
- **Orden de la comprobación:** primero el ETag (si coincide, no ha cambiado) y después el hash.
- **`mark_verified` usa `COALESCE(?, columna)`:** si la web no manda cabecera esta vez, se conserva la guardada en vez de sobrescribirla con `NULL`.
- **Ninguna de estas funciones hace `commit`.** Lo hace quien las orquesta, para que una operación a medias no quede guardada.

### La trampa clave: actualizar un índice FTS5 de contenido externo

`pages_fts` se crea con `content='pages'` y sin triggers, así que no se entera de que `pages` ha cambiado y no admite `UPDATE`. Para sustituir contenido hay que seguir este orden exacto:

1. **Leer** el contenido viejo (hay que hacerlo antes de sobrescribirlo).
2. **Borrar** su entrada con el comando `'delete'` de FTS5, pasando **exactamente los valores stemizados** con los que se indexó (recalculando `stem_text` sobre el texto viejo).
3. **Actualizar** la fila de `pages`.
4. **Insertar** en `pages_fts` el contenido nuevo stemizado, con el mismo `rowid`.

Nunca se usa el comando `rebuild`. Y el `'delete'` debe ejecutarse **una sola vez**: en una revisión apareció duplicado (uno dentro de un `if` y otro fuera), y borrar dos veces la misma entrada corrompe el índice.

### Problemas encontrados

- **La función "no actualizaba"**: faltaba `con.commit()` en el código de prueba. Sin commit, SQLite descarta la transacción al cerrar la conexión (el `True` solo decía que no hubo errores, no que se hubiera guardado).
- **Texto indexado dos veces:** una prueba pasaba el texto ya stemizado a `replace_content`, que lo guardaba en `extracted_content` (ilegible para el usuario) y lo volvía a stemizar. A las funciones se les pasa siempre el texto **original**; el stemizado es cosa del índice.
- **El hash de las pruebas no seguía la regla** (se calculaba sobre texto crudo, no stemizado).
- **Comprobación del ETag con la cadena `'NULL'`** en vez de `None`: un ETag ausente es `None` en Python.
- **Fechas dos horas por detrás:** ver Punto 2 (UTC).

### Pruebas

`scripts/testing/replacePages/pagesTest.py`. Usan la conexión real pero dentro de un gestor de contexto que hace `rollback()` al salir, así nunca ensucian la base. Comprueban, para cada caso, que la página concreta aparece o no en el índice (y cuántas veces, para detectar duplicados): página inexistente, snippet que pasa a completa, mismo ETag, mismo hash con otro formato, contenido cambiado y doble llamada seguida.

### Pendiente

- **`mark_not_found`** (marcar "original desaparecido" sin borrar la copia). Diseño ya decidido: 404 y 410 → `"gone"` y `original_disappear = 1`; 200 y 304 → `"exists"` y `original_disappear = 0`; cualquier otro código (403, 429, 500...) → `"unknown"` sin tocar nada. Errores corregidos en la revisión: `status_code == 200 or 304` es siempre verdadero (un 500 habría reseteado la marca), y `return print(...)` devuelve `None` en lugar del valor.
- **`insert_page` acepta `last_modified_header` pero no lo guarda:** el parámetro está en la firma, pero el `INSERT` solo lista siete columnas y deja fuera `last_modified_header`. Hay que añadir la columna y su `?` a la sentencia (el punto del checklist "acepta **y guarda** las cabeceras" está a medias).
- **Pruebas por adaptar** a la división de funciones: `replace_content` devuelve ahora `True`/`False`; las pruebas de "mismo ETag" y "mismo hash" pasan a probar `is_unchanged` y `mark_verified`, y `pagesTest.py` debe importar las funciones de `repository.pages` en vez de tener copia propia.
- **Guardar una página solo con snippet** no tiene función propia: se cubre con `findPageByUrl` + `insert_page(..., state_content='Snippet')`. Se valorará un envoltorio cuando se escriba el orquestador (punto 8).