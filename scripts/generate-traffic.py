#!/usr/bin/env python3
"""
Genera tráfico sintético contra la API usando hilos concurrentes.

Uso:
    python generate-traffic.py --url http://localhost:3000 --duracion 120 --workers 5

Requiere: pip install requests
"""

import argparse
import random
import threading
import time

import requests

# Lista de (método, endpoint, peso). Mayor peso = se llama más seguido.
ENDPOINTS = [
    ("GET", "/", 2),
    ("GET", "/api/datos", 6),
    ("GET", "/api/usuarios", 3),
    ("GET", "/api/usuarios/1", 2),
    ("GET", "/api/usuarios/99", 1),   # 404
    ("GET", "/api/error", 2),         # ~30% 500
    ("GET", "/api/lento", 1),         # 2-3 s
    ("POST", "/api/items", 1),
]

_stop = threading.Event()
_lock = threading.Lock()
_contador = {"ok": 0, "error": 0}


def elegir_endpoint():
    metodos, rutas, pesos = zip(*[(m, r, w) for m, r, w in ENDPOINTS])
    idx = random.choices(range(len(ENDPOINTS)), weights=pesos, k=1)[0]
    return ENDPOINTS[idx][0], ENDPOINTS[idx][1]


def worker(base_url):
    while not _stop.is_set():
        metodo, ruta = elegir_endpoint()
        url = base_url + ruta
        try:
            if metodo == "POST":
                r = requests.post(url, json={"nombre": "item"}, timeout=10)
            else:
                r = requests.get(url, timeout=10)
            with _lock:
                if r.status_code < 400:
                    _contador["ok"] += 1
                else:
                    _contador["error"] += 1
            print(f"{r.status_code} {metodo} {ruta}")
        except requests.RequestException as exc:
            with _lock:
                _contador["error"] += 1
            print(f"ERR {metodo} {ruta}: {exc}")
        time.sleep(random.uniform(0.05, 0.4))


def main():
    parser = argparse.ArgumentParser(description="Generador de tráfico sintético")
    parser.add_argument("--url", default="http://localhost:3000", help="URL base de la API")
    parser.add_argument("--duracion", type=int, default=120, help="Duración en segundos")
    parser.add_argument("--workers", type=int, default=5, help="Número de hilos concurrentes")
    args = parser.parse_args()

    print(f"Generando tráfico hacia {args.url} con {args.workers} workers "
          f"durante {args.duracion}s (Ctrl+C para detener)...")

    hilos = [threading.Thread(target=worker, args=(args.url,), daemon=True)
             for _ in range(args.workers)]
    for h in hilos:
        h.start()

    try:
        time.sleep(args.duracion)
    except KeyboardInterrupt:
        print("\nDetenido por el usuario.")
    finally:
        _stop.set()
        time.sleep(0.5)

    print(f"\nTotal -> OK: {_contador['ok']}  Errores/4xx-5xx: {_contador['error']}")


if __name__ == "__main__":
    main()
