# OhMyData

> **Proyecto temporalmente en pausa por falta de tiempo.**
> El desarrollo está detenido de momento. El código y la documentación se mantienen tal cual, y el estado exacto en que se ha quedado cada parte está descrito en la sección [Estado actual](#estado-actual), para poder retomarlo sin perder contexto.

**Buscador privado y memoria digital personal, autoalojado.**

La Cajita sustituye a Google como puerta de entrada a internet: actúa como intermediario entre tú y los motores de búsqueda públicos, y guarda tu historial de consultas y páginas de interés **exclusivamente en una base de datos local que solo tú controlas**. Ningún tercero recibe ni almacena tu historial de navegación.

## Por qué existe

Los buscadores comerciales guardan tu historial para construir un perfil publicitario sobre ti: el "excedente conductual" que describe Shoshana Zuboff en *La era del capitalismo de la vigilancia*. La Cajita invierte ese modelo. La base de datos es tuya por diseño, y cualquier motor de búsqueda o modelo de IA que la use es una pieza sustituible, nunca el dueño del dato.

Precedente histórico: *Aware Home* (Georgia Tech, 2000), un hogar inteligente con soberanía total del dato que nunca escaló porque no existía un modelo de negocio compatible con datos que solo pertenecían al usuario.

## Regla de diseño principal

> **La Cajita solo contacta con una web de origen cuando el usuario elige esa página.**

- **Buscar** nunca toca webs de origen: se resuelve en local, o se habla solo con los motores de búsqueda vía SearXNG.
- **Abrir** una página es el único momento en que se descarga (si es nueva) o se revalida (si ya estaba guardada).

Motivo: descargar todos los resultados de cada búsqueda en el mismo segundo reproduce la página de resultados y permite deducir qué buscó el usuario cruzando horas y dominios.

## Arquitectura

### Flujo

```
BUSCAR
  Consulta del usuario
    ├─> 1. Búsqueda local (SQLite + FTS5, texto stemizado, ranking BM25)
    └─> 2. Si no hay resultados locales suficientes:
             SearXNG (Brave + DuckDuckGo + Mojeek)
             → se guarda título, URL y snippet de cada resultado
             → no se descarga ninguna web
    → Se registra la búsqueda y su relación con las páginas (N:M)

ABRIR (el usuario elige un resultado)
  ├─> Página solo con snippet → se descarga, se extrae el contenido
  │                             y se guardan contenido, hash y cabeceras
  └─> Página ya guardada:
        ¿verificada hace poco?  → se sirve la copia local, sin contactar la web
        si no, revalidación:
          ETag           → If-None-Match
          Last-Modified  → If-Modified-Since
          ninguna        → descarga y comparación de hash
        304 → copia local válida
        200 → se actualiza contenido, hash y cabeceras
        404/410 → se conserva la copia (caché anti-404)
```

### Motores de búsqueda (vía SearXNG)

**Brave, DuckDuckGo y Mojeek**, elegidos por tener índices propios y distinta sensibilidad de privacidad. Mojeek exige resolver un CAPTCHA de tipo Proof-of-Work, que en las pruebas duplicó la latencia (~0,8 s → ~1,5 s). Se mantiene activo, pendiente de reevaluar en el hardware final.

### Base de datos (SQLite + FTS5)

- Tablas: `searches`, `pages`, `search_page` (relación N:M) y `pages_fts` (tabla virtual FTS5).
- `pages_fts` solo almacena raíces stemizadas en español (`snowballstemmer`). La inserción y la consulta deben pasar por el mismo stemming o las raíces no coinciden.
- El hash de contenido se calcula sobre el texto stemizado, para que cambios de formato (espacios, saltos, mayúsculas) no se detecten como cambios reales.
- Benchmarks: con términos comunes FTS5 es ~1,3-1,7x más rápido que `LIKE`; con un término único, ~754x, gracias al índice invertido.

### Red

- Servidor de coordinación propio con **Headscale**, y el cliente libre `tailscaled` (BSD-3-Clause) apuntando a él. No se usa el servicio comercial de Tailscale.
- Conexión en 3 capas para funcionar tras CG-NAT: IPv6 directo, P2P vía STUN sobre IPv4 y, como último recurso, un relay DERP propio sin persistencia que solo reenvía paquetes ya cifrados.
- Aislamiento Docker: solo SearXNG tiene salida a internet; la base de datos y el SLM viven en una red interna sin salida.

### SLM (opcional)

Modelo de lenguaje local para tareas en segundo plano (resúmenes, etiquetado, relevancia de cambios). Nunca decide el ranking ni qué datos se guardan. El sistema funciona sin él.

### Modelo de amenaza

Protección frente al **perfilado publicitario masivo**, no frente a adversarios con capacidad de vigilancia de red. La descarga de páginas sale con la IP del usuario, sin cookies ni JavaScript; la operadora y las CDNs grandes aún pueden observar patrones de dominios.

## Estructura del repositorio

```
db/
  schema.sql
scripts/
  db/connection.py              # ruta de la BBDD y conexión
  repository/pages.py           # guardado y búsqueda de páginas
  repository/searches.py        # registro de búsquedas
  freshness/hash_utils.py       # cálculo y comparación de hashes
  search/local_search.py        # búsqueda local (FTS5 + BM25)
  steming.py                    # tokenización y stemming en español
  testing/                      # benchmarks y datos de prueba
  main.py                       # punto de entrada por terminal
docker/
  searxng-config/settings.yml   # configuración de SearXNG
docs/
  bitacoras/                    # bitácora semanal por bloque
```

## Estado actual

| Bloque | Contenido | Estado |
|---|---|---|
| 1 | Marco teórico y licencias | ✅ Terminado |
| 2 | SQLite + FTS5, stemming en español, benchmarks | ✅ Terminado |
| 3 | Red (Headscale, 3 capas, DERP propio) | ✅ Red terminada · ⏳ falta el Docker del proyecto completo |
| 4a | SearXNG | 🟡 A medias |
| 4b | SLM local | ⏳ Sin empezar |
| 5 | Integración y propuesta de financiación | ⏳ Sin empezar |

**Dónde se quedó el Bloque 4a:**

- Hecho: SearXNG desplegado en Docker con los tres motores, consumo de su API JSON desde Python, y `hash_utils.py`.
- Diseñado pero sin implementar: columnas nuevas del esquema (`etag`, `last_modified_header`, `last_verified_at`, estado snippet/completo), extractor de contenido con `requests` + `trafilatura`, `freshness_checker`, orquestador con las operaciones Buscar y Abrir.
- El plan detallado está en `docs/checklist-algoritmo-busqueda.md`.

## Financiación

El proyecto se estaba preparando para presentarse a [NLnet](https://nlnet.nl/) (fondo Restack). Con la pausa, la convocatoria de noviembre de 2026 queda descartada. La propuesta se retomará cuando se reanude el desarrollo.

## Licencias

- Código: AGPLv3
- Hardware: CERN-OHL-S 2.0
- Documentación: CC BY-SA 4.0

## Autores

Davi y Antonio, Sevilla, España.
