# Monitoreo y Observabilidad — API REST con Prometheus y Grafana

> **Nombre:** _Juan Carlos Rojas Lizarazo_
> **Código de estudiante:** _202222901601_
> **Repositorio:** _https://github.com/ingjuancrojasl-crypto/monitoreo-observabilidad_
> **Video:** _[URL de tu video]_

Stack completo de monitoreo y observabilidad ejecutado con Docker Compose. Incluye una
API REST instrumentada con métricas en formato Prometheus, recolección con Prometheus,
visualización con Grafana (dashboard provisionado automáticamente), alertas y un
generador de tráfico sintético.

---

## Arquitectura

```
                 scrape /metrics cada 15s
  ┌─────────┐  ◄─────────────────────────  ┌────────────┐      consulta      ┌─────────┐
  │   API   │                              │ Prometheus │  ◄───────────────  │ Grafana │
  │ :3000   │  ─────────────────────────►  │   :9090    │  ───────────────►  │  :3001  │
  └─────────┘     expone métricas          └────────────┘                    └─────────┘
       ▲
       │  tráfico sintético (script)
  ┌─────────────┐
  │   scripts   │
  └─────────────┘
```

- **API** (FastAPI + `prometheus-client`): expone los endpoints de negocio y `/metrics`.
- **Prometheus**: hace *scraping* del endpoint `/metrics` cada 15 segundos y evalúa alertas.
- **Grafana**: consulta a Prometheus y muestra el dashboard (datasource y dashboard
  se cargan solos vía *provisioning*).

---

## Estructura del proyecto

```
monitoreo-observabilidad/
├── docker-compose.yml
├── README.md
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py
├── prometheus/
│   ├── prometheus.yml
│   └── alerts.yml
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/datasource.yml
│   │   └── dashboards/dashboards.yml
│   └── dashboards/
│       └── api-dashboard.json
└── scripts/
    ├── generate-traffic.sh
    └── generate-traffic.py
```

---

## Cómo ejecutar

Requisito: Docker y Docker Compose instalados.

```bash
# 1. (Opcional) limpiar todo de cero
docker-compose down -v

# 2. Construir y levantar los 3 servicios
docker-compose up -d --build

# 3. Verificar que los servicios están corriendo
docker-compose ps
```

Accesos:

| Servicio        | URL                                                                           | Credenciales      |
|-------------    |-------------------------------------------------------------------------------|-------------------|
| API             | http://localhost:3000                                                         | —                 |
| API/datos       | http://localhost:3000/api/datos                                               | —                 |
| API/lento       | http://localhost:3000/api/lento                                               | —                 |
| API/usuarios    | http://localhost:3000/api/usuarios                                            | —                 |
| API/usuarios/99 | http://localhost:3000/api/usuarios/99                                         | —                 |
| API/error       | http://localhost:3000/api/error                                               | —                 |
| Métricas        | http://localhost:3000/metrics                                                 | —                 |
| Prometheus      | [http://localhost:9090](http://localhost:9090/query?g0.expr=rate%28http_requests_total%5B1m%5D%29%0A&g0.show_tree=0&g0.tab=table&g0.range_input=1h&g0.res_type=auto&g0.res_density=medium&g0.display_mode=lines&g0.show_exemplars=0&g1.expr=rate%28http_request_duration_seconds_sum%5B1m%5D%29+%2F+rate%28http_request_duration_seconds_count%5B1m%5D%29&g1.show_tree=0&g1.tab=table&g1.range_input=1h&g1.res_type=auto&g1.res_density=medium&g1.display_mode=lines&g1.show_exemplars=0)| —                 |
| Grafana        | http://localhost:3001/d/api-monitoring/monitoreo-de-api-
                observabilidad?orgId=1&from=now-15m&to=now&timezone=browser&refresh=5s        | admin1 / admin1   |
                

En Grafana el dashboard **"Monitoreo de API - Observabilidad"** aparece ya cargado
(menú **Dashboards**). El datasource de Prometheus también queda configurado solo.

---

## Endpoints de la API

| Método | Endpoint               | Descripción                                          |
|--------|------------------------|------------------------------------------------------|
| GET    | `/`                    | Información del servicio y lista de endpoints         |
| GET    | `/api/datos`           | Devuelve datos rápidos (respuesta inmediata)          |
| GET    | `/api/lento`           | Simula procesamiento lento (2–3 s)                    |
| GET    | `/api/usuarios`        | Lista de usuarios                                     |
| GET    | `/api/usuarios/{id}`   | Usuario por id (404 si no existe)                     |
| POST   | `/api/items`           | Crea un item e incrementa una métrica de negocio      |
| GET    | `/api/error`           | Falla ~30% de las veces (para ver la tasa de errores) |
| GET    | `/health`              | Healthcheck                                           |
| GET    | `/metrics`             | Métricas en formato Prometheus                        |

> Son 8 endpoints de negocio + `/metrics`, superando el mínimo de 3 (cuenta para el bonus).

---

## Métricas implementadas

| Métrica                              | Tipo      | Descripción                                              |
|--------------------------------------|-----------|----------------------------------------------------------|
| `http_requests_total`                | Counter   | Total de requests por `method`, `endpoint` y `status`    |
| `http_request_duration_seconds`      | Histogram | Latencia de las requests (permite p50/p95/p99)           |
| `http_requests_in_progress`          | Gauge     | Requests procesándose en este instante                   |
| `api_system_cpu_percent`             | Gauge     | Uso de CPU del proceso de la API                         |
| `api_system_memory_bytes`            | Gauge     | Memoria residente (RSS) del proceso de la API            |
| `api_items_created_total`            | Counter   | Items creados vía POST (métrica de negocio)              |

La instrumentación se hace con un **middleware** que mide automáticamente cada petición,
así que no hay que tocar cada endpoint a mano.

---

## Generar tráfico sintético

Con el stack levantado, ejecuta uno de los scripts:

```bash
# Opción Bash (requiere curl)
bash scripts/generate-traffic.sh http://localhost:3000 120

# Opción Python (requiere: pip install requests)
python scripts/generate-traffic.py --url http://localhost:3000 --duracion 120 --workers 5
```

El script reparte peticiones entre todos los endpoints (incluyendo el lento, el de
errores y POST), para que los paneles muestren patrones interesantes.

---

## Queries PromQL del dashboard

```promql
# Throughput total (requests por segundo)
sum(rate(http_requests_total[1m]))

# Throughput por endpoint
sum by (endpoint) (rate(http_requests_total[1m]))

# Latencia p95 (percentil 95) usando el histograma
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))

# Latencia promedio
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])

# Tasa de errores 5xx (%)
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100

# Requests activos ahora mismo
sum(http_requests_in_progress)
```

---

## Dashboard de Grafana

El dashboard provisionado incluye 8 paneles (supera el mínimo de 3):

1. **Throughput total (req/s)** — KPI.
2. **Requests activos** — KPI (gauge).
3. **Latencia p95** — KPI con umbrales de color.
4. **Tasa de errores 5xx (%)** — KPI con umbrales.
5. **Throughput por endpoint** — series de tiempo.
6. **Latencia p50 / p95 / p99** — percentiles con `histogram_quantile()`.
7. **Tasa de errores por código HTTP** — series de tiempo.
8. **Recursos del sistema (CPU y memoria)** — series de tiempo.

---

## Alertas (bonus)

Definidas en `prometheus/alerts.yml` y visibles en Prometheus → **Alerts**:

- **ApiCaida**: la API no responde al *scrape* durante 30 s.
- **LatenciaAlta**: el p95 supera 1 s durante 1 minuto.
- **TasaErroresAlta**: más del 10% de respuestas 5xx durante 1 minuto.

---

## Análisis y posibles optimizaciones

Las métricas permiten ver de un vistazo el throughput, la latencia por percentiles y la
tasa de errores. El endpoint `/api/lento` domina la latencia p95/p99 porque tarda 2–3 s;
una optimización clara sería **cachear su resultado o procesarlo de forma asíncrona**
para sacarlo de la ruta crítica. Si el panel de errores 5xx se dispara, el siguiente paso
sería revisar logs del endpoint `/api/error`. El gauge de requests activos ayuda a detectar
saturación: si crece sin bajar, la API no está drenando peticiones lo bastante rápido y
habría que escalar horizontalmente (más réplicas) o subir la concurrencia de uvicorn.

---

## Detener el stack

```bash
docker-compose down       # detiene los servicios
docker-compose down -v    # detiene y borra los volúmenes (datos de Prometheus/Grafana)
```
