# Guion para el video (máx. 5 minutos)

> El límite de 5:00 es estricto. Practica una vez y edita las pausas.
> Recuerda: **debes aparecer tú en el video** durante la demostración (webcam en una esquina).

---

## 1. Introducción — 30 s
- Saluda y di tu **nombre completo y código**.
- "Esta es una API REST construida con FastAPI, instrumentada con métricas de
  Prometheus, y monitoreada con Prometheus + Grafana, todo en Docker."
- Explica en una frase qué hace la API: expone varios endpoints (datos rápidos,
  un endpoint lento, usuarios, etc.) y un endpoint `/metrics`.

## 2. Demostración técnica — 3 min
1. **Levantar el stack** (ten esto ya casi listo para no perder tiempo):
   ```bash
   docker-compose up -d --build
   docker-compose ps
   ```
   Muestra los **3 servicios corriendo** (api, prometheus, grafana).
2. **API**: abre http://localhost:3000 y muestra `/api/datos`, `/api/lento`,
   `/api/usuarios`. Explica brevemente cada uno.
3. **Métricas**: abre http://localhost:3000/metrics y señala
   `http_requests_total`, `http_request_duration_seconds` y `http_requests_in_progress`.
4. **Tráfico**: ejecuta el script en otra terminal:
   ```bash
   bash scripts/generate-traffic.sh
   ```
5. **Prometheus** (http://localhost:9090): ejecuta al menos 2 queries:
   - `sum(rate(http_requests_total[1m]))`
   - `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))`
   (Opcional bonus: muestra la pestaña **Alerts**.)
6. **Grafana** (http://localhost:3001, admin/admin): abre el dashboard
   "Monitoreo de API - Observabilidad" y muestra los paneles (al menos 3).

## 3. Análisis — 1 min
- Di qué se monitorea: throughput, latencia por percentiles, tasa de errores, recursos.
- Interpreta: "El p95 sube por culpa de `/api/lento` que tarda 2–3 s."
- Optimización: "Se podría cachear o hacer asíncrono `/api/lento` para bajar el p95."

## 4. Cierre — 30 s
- "El monitoreo permite detectar problemas antes que los usuarios y decidir con datos
  cuándo escalar u optimizar." Despídete.

---

### Checklist antes de grabar
- [ ] `docker-compose down -v` y luego `docker-compose up -d --build` para empezar limpio.
- [ ] Webcam activa (tú en pantalla).
- [ ] Tráfico generándose para que los paneles tengan datos.
- [ ] Cronometra: que no pase de 5:00.
