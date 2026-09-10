# Bitácora — Bloque 2: Base de Datos y Búsqueda de Texto Completo
 
**Periodo:** septiembre 2026
**Objetivo del bloque:** entender y construir la capa de memoria local (SQLite + FTS5) que sostiene toda la arquitectura de La Cajita.
 
---
 
## Semana 1 — Esquema de la base de datos
 
### Decisiones tomadas
 
- Relación **N:M** entre búsquedas y páginas (una búsqueda devuelve varias páginas; una misma página puede aparecer en varias búsquedas), resuelta con una tabla de unión (`search_page`) para evitar duplicar contenido.
- Campo `url TEXT NOT NULL UNIQUE` en `pages` para garantizar que la misma página nunca se guarda dos veces.
- Nomenclatura del esquema decidida en inglés desde el inicio (`searches`, `pages`, `search_page`), tras acordar como regla de proyecto que todo el código vive en inglés.
- El repositorio se reinició desde cero durante esta fase para arrancar limpio con la nomenclatura en inglés, el reparto de bloques por persona y las reglas de trabajo ya definidas (ver `RULES.md`).
### Esquema (`schema.sql`)
 
Tablas: `searches` (id, query, timestamp), `pages` (id, url, title, extracted_content, content_hash, saved_at, last_changed_at), `search_page` (tabla de unión N:M con result_position), y la tabla virtual `pages_fts` (FTS5, external content sobre `pages`).
 
---
 
## Semana 2 — FTS5: tabla virtual y primeras búsquedas
 
### Decisiones tomadas
 
- Tabla virtual FTS5 creada como **"external content"** (`content='pages'`), para no duplicar el texto ya guardado en la tabla normal.
- Se probó inicialmente la sincronización mediante **triggers** (`AFTER INSERT/UPDATE/DELETE`), pero se eliminaron al incorporar el preprocesado de stemming en español (Semana 3): al insertar mediante script Python, la sincronización de `pages_fts` pasa a ser responsabilidad explícita del propio script (inserción manual en dos pasos: contenido original en `pages`, contenido stemizado en `pages_fts`), evitando que el trigger duplique o pise la versión ya procesada.
### Problema encontrado: FTS5 no disponible en DB Browser (apt/dnf)
 
- El paquete `sqlitebrowser` instalado vía `apt`/`dnf` no trae FTS5 compilado; el `CREATE VIRTUAL TABLE ... USING fts5(...)` fallaba con `no such module: fts5`.
- **Solución**: usar la CLI `sqlite3` (que sí lo soporta) para crear el esquema, y DB Browser reinstalado vía **Flatpak** (build de Flathub, sí compilada con FTS5) para inspección visual de los datos.

---

## Semana 3 — Benchmarking: Escaneo secuencial vs Índice invertido

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