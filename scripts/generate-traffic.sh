#!/usr/bin/env bash
# Genera tráfico sintético contra la API para observar patrones en Grafana.
# Uso:  ./generate-traffic.sh [URL_BASE] [DURACION_SEGUNDOS]
# Ejemplo: ./generate-traffic.sh http://localhost:3000 120

set -u

BASE_URL="${1:-http://localhost:3000}"
DURACION="${2:-120}"   # segundos

echo "Generando tráfico hacia $BASE_URL durante $DURACION segundos..."
echo "Pulsa Ctrl+C para detener."

FIN=$(( $(date +%s) + DURACION ))

# Pesos: pegamos más a los endpoints rápidos y de vez en cuando al lento/error.
ENDPOINTS=(
  "/"
  "/api/datos"
  "/api/datos"
  "/api/datos"
  "/api/usuarios"
  "/api/usuarios/1"
  "/api/usuarios/99"   # genera 404
  "/api/error"
  "/api/lento"
)

peticiones=0
while [ "$(date +%s)" -lt "$FIN" ]; do
  ep="${ENDPOINTS[$RANDOM % ${#ENDPOINTS[@]}]}"
  curl -s -o /dev/null -w "%{http_code} %{time_total}s -> $ep\n" "$BASE_URL$ep"
  peticiones=$((peticiones + 1))

  # Cada ~15 peticiones, crear un item con POST.
  if [ $((peticiones % 15)) -eq 0 ]; then
    curl -s -o /dev/null -X POST "$BASE_URL/api/items" \
      -H "Content-Type: application/json" \
      -d '{"nombre":"item de prueba"}'
  fi

  # Pausa aleatoria corta entre peticiones (0.05 - 0.4s).
  sleep "0.$((RANDOM % 4 + 1))"
done

echo "Listo. Se enviaron $peticiones peticiones."
