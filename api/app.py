"""
API REST instrumentada con métricas de Prometheus.

Actividad: Monitoreo y observabilidad
Stack: FastAPI + prometheus-client + psutil

La API expone varios endpoints de ejemplo y un endpoint /metrics en
formato Prometheus. Todas las peticiones se instrumentan automáticamente
mediante un middleware que registra:
  - Total de requests (Counter) por método, endpoint y código de estado.
  - Latencia de las requests (Histogram) -> permite p50, p95, p99.
  - Requests en curso (Gauge).
  - Métricas del sistema (CPU y memoria) actualizadas en cada scrape.
"""

import asyncio
import random
import time

import psutil
from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.requests import Request

# ---------------------------------------------------------------------------
# Definición de métricas
# ---------------------------------------------------------------------------
# Usamos un registry propio para tener control total de lo que se expone.
REGISTRY = CollectorRegistry()

# 1. Contador de requests totales (etiquetado por método, endpoint y estado).
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Número total de peticiones HTTP procesadas",
    ["method", "endpoint", "status"],
    registry=REGISTRY,
)

# 2. Latencia de requests. El histograma permite calcular percentiles (p95/p99)
#    con histogram_quantile() en PromQL.
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "Duración de las peticiones HTTP en segundos",
    ["method", "endpoint"],
    # Buckets pensados para distinguir endpoints rápidos del endpoint lento (2-3s).
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0),
    registry=REGISTRY,
)

# 3. Requests activos en este instante (gauge sube y baja).
HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Número de peticiones HTTP que se están procesando ahora mismo",
    ["endpoint"],
    registry=REGISTRY,
)

# 4. Métricas del sistema (CPU y memoria del contenedor de la API).
SYSTEM_CPU_PERCENT = Gauge(
    "api_system_cpu_percent",
    "Porcentaje de uso de CPU del proceso de la API",
    registry=REGISTRY,
)
SYSTEM_MEMORY_BYTES = Gauge(
    "api_system_memory_bytes",
    "Memoria residente (RSS) usada por el proceso de la API en bytes",
    registry=REGISTRY,
)

# Métrica de negocio extra (bonus): items "creados" en memoria.
ITEMS_CREATED_TOTAL = Counter(
    "api_items_created_total",
    "Número total de items creados a través de la API",
    registry=REGISTRY,
)

app = FastAPI(
    title="API de Monitoreo y Observabilidad",
    description="API REST de ejemplo instrumentada con métricas de Prometheus.",
    version="1.0.0",
)

# "Base de datos" en memoria para los endpoints de ejemplo.
_DB = {
    "usuarios": [
        {"id": 1, "nombre": "Ada Lovelace", "rol": "ingeniera"},
        {"id": 2, "nombre": "Alan Turing", "rol": "matemático"},
        {"id": 3, "nombre": "Grace Hopper", "rol": "almirante"},
    ],
    "items": [],
}

_PROCESS = psutil.Process()


def _normalizar_endpoint(request: Request) -> str:
    """Devuelve la ruta de la plantilla (p.ej. /api/usuarios/{user_id})
    en lugar de la ruta concreta, para no crear series infinitas en Prometheus."""
    route = request.scope.get("route")
    if route and getattr(route, "path", None):
        return route.path
    return request.url.path


@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    """Middleware que instrumenta TODAS las peticiones automáticamente."""
    endpoint = _normalizar_endpoint(request)

    # No instrumentamos el propio /metrics para no ensuciar las métricas.
    if endpoint == "/metrics":
        return await call_next(request)

    HTTP_REQUESTS_IN_PROGRESS.labels(endpoint=endpoint).inc()
    start = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        elapsed = time.perf_counter() - start
        HTTP_REQUEST_DURATION.labels(
            method=request.method, endpoint=endpoint
        ).observe(elapsed)
        HTTP_REQUESTS_TOTAL.labels(
            method=request.method, endpoint=endpoint, status=str(status_code)
        ).inc()
        HTTP_REQUESTS_IN_PROGRESS.labels(endpoint=endpoint).dec()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/")
async def raiz():
    """Endpoint principal: información básica de la API."""
    return {
        "servicio": "API de Monitoreo y Observabilidad",
        "estado": "ok",
        "endpoints": [
            "/",
            "/api/datos",
            "/api/lento",
            "/api/usuarios",
            "/api/usuarios/{user_id}",
            "/api/items (POST)",
            "/api/error",
            "/health",
            "/metrics",
        ],
    }


@app.get("/api/datos")
async def datos():
    """Endpoint rápido: retorna datos de inmediato."""
    return {
        "timestamp": time.time(),
        "valores": [random.randint(0, 100) for _ in range(5)],
        "mensaje": "Datos generados correctamente",
    }


@app.get("/api/lento")
async def lento():
    """Simula un procesamiento lento (entre 2 y 3 segundos)."""
    retraso = random.uniform(2.0, 3.0)
    await asyncio.sleep(retraso)
    return {"mensaje": "Procesamiento completado", "duracion_segundos": round(retraso, 3)}


@app.get("/api/usuarios")
async def listar_usuarios():
    """Bonus: retorna la lista de usuarios."""
    return {"total": len(_DB["usuarios"]), "usuarios": _DB["usuarios"]}


@app.get("/api/usuarios/{user_id}")
async def obtener_usuario(user_id: int):
    """Bonus: retorna un usuario por id (404 si no existe)."""
    for usuario in _DB["usuarios"]:
        if usuario["id"] == user_id:
            return usuario
    return JSONResponse(status_code=404, content={"error": "Usuario no encontrado"})


@app.post("/api/items")
async def crear_item(item: dict):
    """Bonus: crea un item en memoria e incrementa una métrica de negocio."""
    nuevo = {"id": len(_DB["items"]) + 1, **item}
    _DB["items"].append(nuevo)
    ITEMS_CREATED_TOTAL.inc()
    return JSONResponse(status_code=201, content={"creado": nuevo})


@app.get("/api/error")
async def error_aleatorio():
    """Bonus: devuelve un error ~30% de las veces para visualizar la tasa de errores."""
    if random.random() < 0.3:
        return JSONResponse(status_code=500, content={"error": "Error simulado"})
    return {"mensaje": "Todo bien esta vez"}


@app.get("/health")
async def health():
    """Healthcheck simple."""
    return {"status": "healthy"}


@app.get("/metrics")
async def metrics():
    """Expone las métricas en formato Prometheus."""
    # Actualizamos métricas del sistema en el momento del scrape.
    SYSTEM_CPU_PERCENT.set(_PROCESS.cpu_percent(interval=None))
    SYSTEM_MEMORY_BYTES.set(_PROCESS.memory_info().rss)
    data = generate_latest(REGISTRY)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
