# Reglas del proyecto — La Cajita

Documento de referencia fijo. Cualquier cambio a estas reglas se discute entre los dos antes de aplicarlo.

## Idioma y código

- Código siempre en inglés: nombres de tablas, columnas, variables, funciones, clases.
- Comentarios en el código: en inglés.
- Commits y nombres de ramas: en inglés.
- README principal en inglés (opcionalmente `README.es.md` como espejo, si hay tiempo).
- La bitácora de desarrollo sí puede escribirse en español (uso interno).

## Git — ramas y commits

- Rama corta por tarea/pieza con entidad propia (`feature/fts5-schema`, `feature/tailscale-setup`...). Cambios pequeños que no rompen nada pueden ir directos a `main`.
- Fusionar directo a `main` cuando la pieza funcione y esté probada — sin rama intermedia tipo `develop`.
- `main` siempre debe quedar en estado funcional, nunca con código roto a medias.
- Mensajes de commit descriptivos, en inglés (se puede usar IA como ayuda para redactar el mensaje, pero debe describir con precisión lo que cambia).
- Antes de hacer merge a `main`, probar que lo que se añade no rompe lo que ya funcionaba.

## Reparto de bloques

| Bloque | Responsable |
|---|---|
| 1 — Soberanía de datos y marco teórico | Ambos |
| 2 — SQLite + FTS5 | Davi |
| 3 — Docker + Tailscale | Antonio |
| 4a — SearXNG | Davi |
| 4b — SLM local | Antonio |
| 5 — Integración MVP + propuesta NLnet | Ambos |

- Cada uno es responsable último de su bloque, pero ambos deben entender lo suficiente del bloque del otro como para poder explicarlo si hace falta (sobre todo de cara a la propuesta de NLnet, que la puede leer cualquiera de los dos).

## Documentación

- **Bitácora semanal** (`docs/bitacora-bloqueN.md`): qué se ha avanzado esa semana, decisiones tomadas y por qué, problemas encontrados y cómo se resolvieron. Se escribe cada semana, no se deja acumular para el final del bloque.
- **Nota de traspaso** (`docs/notas/bloqueN-<responsable>.md`): cada uno, al avanzar en su bloque, deja un `.md` corto explicando lo que el compañero necesita saber sí o sí para no perderse (decisiones de arquitectura, cómo ejecutar/probar lo que se ha hecho, dependencias nuevas instaladas). No es un README técnico exhaustivo, es un resumen dirigido a la otra persona.
- Toda decisión que se descarte activamente (ej. "no usamos Tor en el MVP por sobreingeniería") se anota también, no solo lo que se decide hacer — es tan útil para la propuesta de NLnet como lo que sí se construye.

## Reglas añadidas (sugeridas)

- **`requirements.txt` actualizado en cada commit que añada una dependencia nueva** — nunca lo dejéis desactualizado, o el entorno de uno no será reproducible por el otro.
- **`.gitignore` correcto desde el primer commit** (`.venv/`, `__pycache__/`, `*.db` si no queréis subir bases de datos de prueba con datos locales, `*.pyc`).
- **Código público desde el primer commit del repo**, no privado hasta "que esté bonito" — NLnet exige que el código esté público desde el día 1, así que mejor acostumbrarse ya a trabajar en abierto.
- **Nada de texto generado por IA sin reescribir en la propuesta final** — se puede usar como apoyo para pensar y estructurar, pero el documento que se envíe a NLnet debe estar redactado por vosotros, con vuestras palabras (política explícita de NLnet contra propuestas generadas por IA).
- **Sincronización semanal corta** (15-20 min, aunque sea por videollamada): repasar qué se ha hecho, qué bloquea a quién, y si algo del bloque de uno afecta al del otro antes de que se descubra tarde.
- **Definición de "hecho" por bloque**: antes de dar un bloque por cerrado, confirmar explícitamente que (a) el código está en `main`, (b) la bitácora de ese bloque está escrita, (c) la nota de traspaso existe si aplica, (d) el compañero ha revisado al menos por encima el resultado.
- **Un Issue de GitHub por tarea relevante**, enlazado a la tarjeta del Kanban — evita que las tareas vivan solo "en la cabeza" de cada uno.
- **No ampliar el alcance de un bloque sin comentarlo antes con el otro** (evitar que, por ejemplo, Bloque 4a se convierta en meses por ir añadiendo ideas nuevas de SearXNG sin avisar) — si surge una idea nueva a mitad de bloque, se anota para "trabajo futuro" en vez de meterla de inmediato.

## Evitar y resolver conflictos de Git

El reparto por bloques hace que el solapamiento sea bajo la mayoría del tiempo (archivos y carpetas distintas), pero en el Bloque 5 (integración) es donde más probable es que los dos toquéis el mismo código a la vez. Reglas para minimizarlo:

- **Ramas de vida corta**: fusionar a `main` en cuanto una pieza funcione y esté probada, no dejar una rama abierta acumulando días de trabajo — cuanto más tiempo pasa, más se desvía de lo que el otro está haciendo y mayor el conflicto al fusionar.
- **`git pull` (o `fetch` + `merge origin/main`) al empezar cada sesión**: traer los cambios ya fusionados del otro antes de seguir trabajando, para que los conflictos pequeños vayan apareciendo poco a poco en vez de todos de golpe al final.
- **Avisar si se va a tocar un archivo que también toca el otro** (aunque sea un simple mensaje de chat: "hoy toco `backend.py`") — con solo dos personas, esto evita la mayoría de los choques sin necesidad de herramientas complicadas.
- **Commits pequeños y frecuentes**, no uno gigante al final del bloque — un conflicto de pocas líneas se resuelve en minutos; uno de cientos de líneas cambiadas en ambos lados es mucho más costoso.
- **Al resolver un conflicto**: parar, mirar juntos (o por chat) las dos versiones en conflicto, decidir con calma qué se queda o cómo se combinan, y hacer un commit normal confirmando la resolución — nunca se pierde trabajo, ambas versiones quedan visibles hasta que se decide.
