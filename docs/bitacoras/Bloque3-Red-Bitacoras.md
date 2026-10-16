# Bitácora — Bloque 3: Infraestructura, Contenedorización y Red Soberana

**Periodo:** octubre 2026
**Responsable:** Antonio
**Objetivo del bloque:** Diseñar, desplegar y asegurar la infraestructura de red descentralizada (Headscale/Tailscale) y la arquitectura de contenedores (Docker) que aislará el flujo de datos en "La Cajita", garantizando el principio de soberanía y el *Air-Gap* por diseño para los modelos de IA.

---

## Punto 1 — El Plano de Control: Red Soberana y Evasión de CG-NAT

### Decisiones de Diseño (Infraestructura Central)
Se descartó depender de los servidores oficiales de *Tailscale Inc.* para evitar puntos únicos de fallo y la exfiltración de telemetría hacia terceros. Se optó por **Headscale (v0.29.3)** autohospedado sobre un Ubuntu Server. 

Para blindar la soberanía de los datos y asegurar cero fugas de metadatos, se aplicó una modificación clave de seguridad en el archivo `config.yaml` del servidor central, configurando el bloque de enrutamiento DERP de la siguiente manera:

```yaml
derp:
  server:
    enabled: true
    region_id: 999
    region_code: "omd"
    region_name: "OMD Soberana DERP"
    stun_listen_addr: "0.0.0.0:3478"
    private_key_path: /var/lib/headscale/derp_server_private.key
  urls: []
  paths: []
  auto_update_enabled: false
```

**Justificación Técnica:** Al dejar los arrays `urls: []` y `paths: []` vacíos, y al desactivar explícitamente `auto_update_enabled`, se corta de raíz cualquier posibilidad de que Headscale consulte la API de Tailscale para descargar su lista de servidores públicos. El tráfico de la red OMD queda confinado a dos vías físicas exclusivas: una conexión P2P directa mediante perforación de NAT, o el uso exclusivo del relé DERP alojado en la memoria de nuestro propio servidor (puerto UDP 3478).

### Problema Arquitectónico: Hardware de operadora y CG-NAT
- **Contexto:** El servidor central se aloja bajo una conexión residencial (Digi) con un CG-NAT estricto. El router proporcionado por la operadora (TP-Link) bloquea activamente los puertos de entrada 80 (HTTP) y 443 (HTTPS).
- **Solución Implementada (Reto DNS-01):** Ante la imposibilidad de utilizar el "Reto HTTP-01" para generar los certificados SSL/TLS de *Let's Encrypt*, se desplegó **Nginx Proxy Manager (NPM)** junto a un subdominio de **DuckDNS**. NPM se comunica internamente con la API de DuckDNS para inyectar un registro TXT (Reto DNS-01), logrando emitir el certificado TLS legítimo saltándose el bloqueo del hardware del proveedor. Los clientes atacan el puerto TCP 8443, que NPM redirige de forma segura.

### Validación Empírica (Auditoría P2P)
Para certificar el éxito de la topología antes de pasar a la contenedorización:
1. Se generó el entorno de usuario (`mvp-user`, ID: 1) con una *Pre-Auth Key*.
2. Se conectaron un PC de escritorio (nodo 1: 100.64.0.1) y un dispositivo móvil vía red 5G (nodo 2).
3. El comando `tailscale ping` confirmó un enrutamiento de estado **`direct`**. Se validó empíricamente el *UDP Hole Punching*, demostrando que los nodos pueden atravesar NAT asimétricos sin depender perpetuamente del servidor relay.

---

## Punto 2 — Contenedorización de La Cajita (Docker Compose)

### Topología de Redes (Aislamiento por Capas)
Se rechazó categóricamente el modelo de red plana (`bridge` por defecto) de Docker. Se estructuró el archivo `docker-compose.yml` en una topología de tres anillos de seguridad estrictos para segmentar el tráfico:
1. **`proxy_net` (Puente de Entrada):** Conecta el agente de Tailscale (`omd-gateway`) con el cerebro de la aplicación (`omd-orchestrator`), permitiendo el acceso remoto seguro.
2. **`frontend_net` (Salida Controlada):** Red exclusiva para que el metabuscador `searxng` pueda salir a internet a interrogar los índices públicos (Brave, DuckDuckGo, Mojeek).
3. **`backend_net` (Aislamiento Total):** Red hermética declarada con la directiva `internal: true`. Confinamiento físico a nivel de Docker para la base de datos (SQLite) y el motor generativo de IA (Ollama).

### El Orquestador y el Entorno de Desarrollo (DX)
- **Construcción Optimizada:** Se redactó un `Dockerfile` utilizando la imagen `python:3.11-slim`. Se descartó `alpine` para el orquestador debido a las carencias de *glibc*, lo cual genera graves cuellos de botella al compilar librerías matemáticas o de *Machine Learning* en Python. Se implementó un sistema de capas que cachea el archivo `requirements.txt` para acelerar las reconstrucciones.
- **Volúmenes Espejo (Bind Mounts):** Para asegurar que la contenedorización no ralentice el flujo de desarrollo del Bloque 4, se vinculó el volumen de código local (`- ./scripts:/app/scripts`). Cualquier modificación en el entorno del *host* se refleja instantáneamente en la memoria del contenedor en ejecución, erradicando la necesidad de comandos `docker build` constantes.

---

## Punto 3 — Validación de Seguridad: El "Air-Gap" Matemático

### Objetivo y Metodología
Demostrar empíricamente y certificar ante NLnet que la arquitectura impide estructuralmente que los modelos de IA local exfiltren datos privados hacia Internet, anulando vectores de ataque incluso si los pesos del modelo o el contenedor resultaran comprometidos.

Se diseñó una prueba de inyección de red: un contenedor ligero (*Alpine Linux*) fue desplegado y forzado a operar exclusivamente dentro del anillo de seguridad interno, intentando resolver un paquete ICMP (ping) hacia una IP pública externa (Cloudflare DNS).

- **Comando de Ejecución:** 
  `docker run --rm --network ohmydata_backend_net alpine ping -c 1 1.1.1.1`
- **Registro del Sistema:**

![Prueba de aislamiento de red (Air-Gap) bloqueando el ping al exterior](img/ping-error.png)

*(Salida de terminal confirmando: `ping: sendto: Network unreachable`)*

### Conclusión Arquitectónica Documentada
La directiva `internal: true` obliga al daemon de Docker a no generar reglas de *NAT masquerade* en las tablas de enrutamiento (*iptables*) del kernel de Linux hacia la interfaz física del host. El sistema operativo destruye los paquetes salientes a nivel de red (Capa 3). La IA y la memoria digital del usuario operan en un búnker criptográfico irrompible desde el interior.

---

## Punto 4 — Evolución Arquitectónica: Estrategia "Dual-SLM" (Edge Computing)

### Desviación Técnica Detectada
La planificación teórica del Bloque 4b sugería la utilización de un LLM cuantizado (ej. Gemma 4B o Qwen 2.5 3B) para labores de enrutamiento y toma de decisiones lógicas en tiempo real.
El análisis de recursos sobre el hardware de destino (*Edge Computing* / Mini PC) demostró que mantener perpetuamente un modelo de 1.5 - 2 GB en memoria RAM para resolver un árbol de decisión booleano ("¿Requiere esta petición una búsqueda en SearXNG?") generaría latencias inaceptables en la interfaz de usuario y comprometería la estabilidad del orquestador y SQLite.

### Implementación Final: Arquitectura Asíncrona de Dos Carriles
Se reestructuró la topología de la inteligencia artificial para maximizar la eficiencia térmica y computacional de La Cajita:

1. **Carril Rápido (Enrutador Lógico Diario):** Se descartó la IA generativa para tareas de categorización. Se integrará un modelo clasificador tipo *Encoder* puramente semántico (ej. *DistilBERT* / *MiniLM*, con un peso de apenas ~90 MB). Este motor matemático se embeberá de forma nativa en la ejecución del script Python (`omd-orchestrator`), evaluando variables de contexto y emitiendo un veredicto de enrutamiento en milisegundos sin latencia perceptible para el usuario.
2. **Carril Pesado (Procesamiento por Lotes Diferido):** La síntesis de texto (resúmenes de páginas web ya indexadas) se mantiene delegada al contenedor `omd-slm` ejecutando *Ollama*. Para evitar el bloqueo de recursos, un *worker* de Python activará este contenedor exclusivamente durante ventanas nocturnas o de inactividad, escaneando las bases de datos en busca de páginas no resumidas. Una vez finalizado el lote, el orquestador forzará la liberación de memoria mediante el parámetro `keep_alive`, purgando el LLM de la RAM y restaurando la capacidad total del Mini PC para su uso diurno.