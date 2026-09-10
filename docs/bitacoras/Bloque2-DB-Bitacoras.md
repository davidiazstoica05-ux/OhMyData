# Bitácora — Bloque 2: Base de Datos y Búsqueda de Texto Completo
 
**Periodo:** septiembre 2026
**Objetivo del bloque:** entender y construir la capa de memoria local (SQLite + FTS5) que sostiene toda la arquitectura de La Cajita.
 
---
 
## Punto 1 — Esquema de la base de datos
 
### Decisiones tomadas
 
- Relación **N:M** entre búsquedas y páginas (una búsqueda devuelve varias páginas; una misma página puede aparecer en varias búsquedas), resuelta con una tabla de unión (`search_page`) para evitar duplicar contenido.
- Campo `url TEXT NOT NULL UNIQUE` en `pages` para garantizar que la misma página nunca se guarda dos veces.
- Nomenclatura del esquema decidida en inglés desde el inicio (`searches`, `pages`, `search_page`), tras acordar como regla de proyecto que todo el código vive en inglés.
- El repositorio se reinició desde cero durante esta fase para arrancar limpio con la nomenclatura en inglés, el reparto de bloques por persona y las reglas de trabajo ya definidas (ver `RULES.md`).
### Esquema (`schema.sql`)
 
Tablas: `searches` (id, query, timestamp), `pages` (id, url, title, extracted_content, content_hash, saved_at, last_changed_at), `search_page` (tabla de unión N:M con result_position), y la tabla virtual `pages_fts` (FTS5, external content sobre `pages`).
 
---
 
## Punto 2 — FTS5: tabla virtual y primeras búsquedas
 
### Decisiones tomadas
 
- Tabla virtual FTS5 creada como **"external content"** (`content='pages'`), para no duplicar el texto ya guardado en la tabla normal.
- Se probó inicialmente la sincronización mediante **triggers** (`AFTER INSERT/UPDATE/DELETE`), pero se eliminaron al incorporar el preprocesado de stemming en español (Semana 3): al insertar mediante script Python, la sincronización de `pages_fts` pasa a ser responsabilidad explícita del propio script (inserción manual en dos pasos: contenido original en `pages`, contenido stemizado en `pages_fts`), evitando que el trigger duplique o pise la versión ya procesada.
### Problema encontrado: FTS5 no disponible en DB Browser (apt/dnf)
 
- El paquete `sqlitebrowser` instalado vía `apt`/`dnf` no trae FTS5 compilado; el `CREATE VIRTUAL TABLE ... USING fts5(...)` fallaba con `no such module: fts5`.
- **Solución**: usar la CLI `sqlite3` (que sí lo soporta) para crear el esquema, y DB Browser reinstalado vía **Flatpak** (build de Flathub, sí compilada con FTS5) para inspección visual de los datos.

### Pruebas de rendimiento (`LIKE` vs `MATCH`)
- **Objetivo:** Validar empíricamente y justificar técnicamente para NLnet la ventaja real de usar FTS5 frente al escaneo de texto tradicional. 
- Se diseñó un experimento controlado en Python con 50.000 filas de prueba (~50MB de texto) y un promedio de 200 ejecuciones por consulta para eliminar el ruido estadístico del recolector de basura (*Garbage Collector*) y de la CPU.

### Evolución de las mediciones y Descubrimiento Técnico
- **Primera medición (Sesgada):** Se obtuvo inicialmente una mejora de apenas **~1.7x** a favor de FTS5. Tras analizar el experimento, se descubrió que el script generaba ruido por falta de promediado y evaluaba una palabra muy común.
- **Benchmark controlado (Extremos de selectividad):**
  - **Término común** ("privacy", presente en miles de registros): FTS5 fue **~1.3x - 1.4x** más rápido.
  - **Término único** ("aguja", presente en 1 solo registro): FTS5 fue **754.6x** más rápido.

### Conclusión Arquitectónica Documentada
El experimento validó la comprensión del comportamiento interno de los motores:
1. `LIKE` tiene un **coste fijo y ciego**: siempre realiza un escaneo secuencial (*Full Table Scan*). Le cuesta la misma cantidad de procesamiento recorrer toda la base de datos para encontrar un término único que uno frecuente.
2. `MATCH` (FTS5) tiene un **coste variable basado en la selectividad**: al utilizar el índice invertido, el coste es proporcional al tamaño de la lista de documentos recuperados (*posting list*). Con un término único el coste es casi nulo, mientras que con un término común el motor debe recuperar y devolver miles de registros, reduciendo la brecha con `LIKE`.

Esta prueba empírica demuestra que FTS5 no es "mágicamente rápido" en abstracto, sino que su eficiencia técnica escala de forma óptima para el caso de uso real de *La Cajita*: recuperar información específica dentro de una memoria digital personal masiva de forma instantánea.

### Batería de Pruebas: `MATCH` (FTS5) vs `LIKE` (Escaneo Secuencial)

Para justificar la arquitectura de *La Cajita* ante NLnet, lanzamos 5 consultas clave contra un dataset de 50.000 registros (~50MB de texto), promediando 200 iteraciones. Se comparó la tabla virtual FTS5 contra un escaneo secuencial tradicional (`LIKE`).

**1. Búsqueda con muchos resultados (Término común: 'privacidad')**
* **FTS5 (`MATCH`):** 13.77 ms (9.985 resultados)
* **SQL (`LIKE`):** 19.05 ms (9.985 resultados)
* **Reflexión técnica:** La ventaja de FTS5 es mínima (1.3x). Al recuperar casi 10.000 coincidencias, el cuello de botella ya no es la búsqueda en el índice, sino el coste de I/O y memoria para que SQLite empaquete y devuelva miles de filas al backend.

**2. Búsqueda de alta selectividad (Término único: 'xilofonomarcador')**
* **FTS5 (`MATCH`):** 0.0142 ms (1 resultado)
* **SQL (`LIKE`):** 10.32 ms (1 resultado)
* **Reflexión técnica:** El escenario óptimo del índice invertido (727x más rápido). Mientras `LIKE` tiene un coste ciego fijo (recorre las 50.000 filas pase lo que pase), FTS5 consulta la *posting list* y recupera la única fila exacta en nanosegundos.

**3. Ranking de Relevancia Masivo ('datos' con BM25)**
* **FTS5 (`ORDER BY rank`):** 111.36 ms (31.332 resultados)
* **SQL (`LIKE` sin ordenación):** 26.72 ms (31.332 resultados)
* **Reflexión técnica:** El cálculo matemático tiene un coste computacional evidente. Calcular la fórmula BM25 y ordenar el 62% de la base de datos penaliza el rendimiento. `LIKE` arroja un mejor tiempo únicamente porque devuelve las filas en bruto, sin calcular su relevancia.

**4. Búsqueda de frase exacta ("motores de búsqueda")**
* **FTS5 (`MATCH`):** Resuelto de forma nativa e instantánea gracias al *positional index* interno, que guarda en qué orden exacto aparecen las palabras.
* **SQL (`LIKE`):** 17.68 ms (9.865 resultados).

**5. Operadores Booleanos complejos (`AND`, `OR`)**
* **FTS5:** 10.75 ms
* **SQL (`LIKE`):** 20.37 ms (6.252 resultados)
* **Reflexión técnica:** FTS5 es el doble de rápido resolviendo intersecciones de conjuntos directamente en la memoria del diccionario. `LIKE` resulta ineficiente al obligar al motor a evaluar múltiples sentencias completas por cada fila escaneada.

---

## Punto 3 — Tokenizadores, stemming e idioma español 

### Pipeline Lingüístico: Tokenización vs Stemming

Para optimizar el índice invertido y permitir coincidencias semánticas reales, se formalizó la distinción técnica de las dos etapas del procesamiento de texto:

* **Tokenizador (Segmentación):** Trocea la cadena de texto continua en unidades léxicas independientes (*tokens* o palabras) mediante expresiones regulares y delimitadores (`[a-záéíóúüñ0-9]+`), normalizando a minúsculas y descartando signos de puntuación.
* **Stemming (Reducción morfológica):** Opera sobre los tokens ya segmentados. Aplica algoritmos de recorte heurístico para remover sufijos, desinencias verbales, plurales y marcas de género, colapsando distintas formas gramaticales a una raíz invariable común (ej. *privacidad* / *privacidades* → `privacid`; *correr* / *corriendo* → `corr`).

$$\text{Texto plano} \longrightarrow \mathbf{Tokenizador} \longrightarrow [\text{Tokens}] \longrightarrow \mathbf{Stemmer} \longrightarrow [\text{Raíces}]$$

---

### Decisión de Arquitectura: Estrategia Bilingüe (Inglés vs Español)

La divergencia morfológica entre ambos idiomas y las limitaciones nativas de SQLite motivaron una solución técnica diferenciada para cada caso:

* **Inglés (Nativo en motor):** Se incorpora la directiva `tokenize='porter'` en la configuración de la tabla virtual FTS5. Dado que SQLite trae el algoritmo de Porter precompilado en C en su binario estándar, el motor procesa el *stemming* anglosajón en memoria sin penalización de I/O ni sobrecarga en el intérprete de Python.
* **Español (Preprocesamiento en aplicación):** Al carecer SQLite de soporte nativo para reglas morfológicas en español sin compilar extensiones dinámicas en C, se implementó un pipeline en el backend mediante la librería `snowballstemmer`.
* **Ratificación del desacoplamiento de triggers:** El procesamiento en español valida la decisión de descartar los *triggers* de sincronización automática. La ingesta de datos se consolida en un flujo manual explícito desde Python:
  1. Persiste el contenido íntegro y original en la tabla relacional `pages` (para renderizado final al usuario).
  2. Ejecuta el pipeline `tokenize` + `snowballstemmer` sobre el texto.
  3. Inserta las raíces resultantes en `pages_fts` vinculadas al mismo `rowid`.
* **Principio de Simetría en Consultas:** Para garantizar que el índice invertido resuelva coincidencias, la cadena de búsqueda introducida por el usuario atraviesa el mismo preprocesamiento en Python antes de invocar la cláusula `MATCH`.
 
