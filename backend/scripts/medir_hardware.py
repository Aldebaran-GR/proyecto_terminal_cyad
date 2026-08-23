"""Mide de dónde salen las cifras de "Requisitos mínimos de hardware" del manual.

Reporta tres cifras + el hardware del host, en tabla y JSON, para que las
recomendaciones del Apéndice C del reporte sean reproducibles.

    - RAM del proceso Django en reposo: arranca ``manage.py runserver --noreload``
      en un subproceso, hace una petición GET a ``/api/v1/healthz/`` (o al root
      del schema) para asegurar que la app está cargada en memoria y muestrea
      ``psutil.Process(pid).memory_info().rss``.
    - RAM de PostgreSQL con la carga de demostración: enumera con ``psutil`` los
      procesos ``postgres`` que estén conectados al puerto configurado en
      ``backend/.env`` (``DB_PORT``) y suma su RSS.
    - Pico de ``npm run build``: lanza ``npm run build`` en ``frontend/`` como
      subproceso y muestrea cada 200 ms el RSS del árbol de procesos, guardando
      el máximo.

Ejecutar desde ``backend/`` con la BD cargada (idealmente vía
``python scripts/seed_demo.py``) y el frontend con ``npm install`` ya
realizado::

    python scripts/medir_hardware.py

Emite dos artefactos: una tabla legible en stdout y un JSON en
``scripts/medir_hardware.out.json`` con la marca de tiempo y el detalle.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    import psutil
except ImportError:
    sys.stderr.write(
        "ERROR: falta psutil. Instale las dependencias del backend con:\n"
        "    pip install -r backend/requirements.txt\n"
    )
    sys.exit(1)

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
OUTPUT_JSON = Path(__file__).resolve().parent / "medir_hardware.out.json"

DJANGO_HOST = "127.0.0.1"
DJANGO_PORT = 8765  # puerto libre elegido para no chocar con el runserver del dev
SAMPLE_INTERVAL_S = 0.2


# ────────────────────────────────────────────────────────────────────────────
# Utilidades
# ────────────────────────────────────────────────────────────────────────────
def mb(bytes_value: int | float) -> float:
    return round(bytes_value / (1024 * 1024), 1)


def leer_env(clave: str, default: str = "") -> str:
    """Lector ligero de backend/.env (no depende de python-decouple)."""
    env_path = BACKEND_DIR / ".env"
    if not env_path.exists():
        return default
    for linea in env_path.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        k, _, v = linea.partition("=")
        if k.strip() == clave:
            return v.strip().strip('"').strip("'")
    return default


def sumar_rss_arbol(pid: int) -> int:
    """RSS del proceso `pid` más el de sus descendientes (Vite/esbuild se ramifican)."""
    try:
        p = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return 0
    total = 0
    with p.oneshot():
        try:
            total += p.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    for hijo in p.children(recursive=True):
        try:
            total += hijo.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return total


# ────────────────────────────────────────────────────────────────────────────
# 1. Django en reposo
# ────────────────────────────────────────────────────────────────────────────
def medir_django_reposo() -> dict:
    """Arranca runserver en un subproceso y mide RSS tras servir una petición."""
    print(f"[1/3] Arrancando Django en {DJANGO_HOST}:{DJANGO_PORT} (subproceso)…")
    manage = BACKEND_DIR / "manage.py"
    cmd = [
        sys.executable,
        str(manage),
        "runserver",
        f"{DJANGO_HOST}:{DJANGO_PORT}",
        "--noreload",
    ]
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    proc = subprocess.Popen(
        cmd,
        cwd=str(BACKEND_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )

    try:
        endpoint = f"http://{DJANGO_HOST}:{DJANGO_PORT}/api/schema/"
        deadline = time.monotonic() + 30
        listo = False
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(endpoint, timeout=1) as resp:
                    resp.read(1024)
                    listo = True
                    break
            except (urllib.error.URLError, ConnectionResetError, socket.timeout):
                time.sleep(0.5)
        if not listo:
            return {
                "ok": False,
                "error": "Django no respondió tras 30 s en /api/schema/.",
            }

        # Espera breve para estabilizar el heap tras servir la primera petición.
        time.sleep(2)
        rss = sumar_rss_arbol(proc.pid)
        return {
            "ok": True,
            "rss_bytes": rss,
            "rss_mb": mb(rss),
            "descripcion": (
                "Proceso Django (runserver --noreload) en reposo tras servir "
                "/api/schema/; incluye el proceso hijo del reloader si lo hubiese."
            ),
        }
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


# ────────────────────────────────────────────────────────────────────────────
# 2. PostgreSQL
# ────────────────────────────────────────────────────────────────────────────
def medir_postgres() -> dict:
    """Suma RSS de todos los procesos `postgres` visibles al usuario actual."""
    print("[2/3] Midiendo procesos de PostgreSQL…")
    db_port = leer_env("DB_PORT", "5432")

    procesos = []
    total = 0
    for p in psutil.process_iter(["pid", "name"]):
        nombre = (p.info["name"] or "").lower()
        if "postgres" not in nombre:
            continue
        try:
            with p.oneshot():
                rss = p.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        procesos.append({"pid": p.info["pid"], "name": p.info["name"], "rss_mb": mb(rss)})
        total += rss

    if not procesos:
        return {
            "ok": False,
            "error": (
                "No se encontraron procesos 'postgres'. ¿Está corriendo el "
                "servicio PostgreSQL en este host?"
            ),
            "db_port": db_port,
        }

    return {
        "ok": True,
        "db_port": db_port,
        "rss_total_bytes": total,
        "rss_total_mb": mb(total),
        "procesos": procesos,
        "descripcion": (
            "Suma del RSS de todos los procesos 'postgres' del host. Refleja "
            "la carga vigente de la BD (ideal: seed_demo ya aplicado)."
        ),
    }


# ────────────────────────────────────────────────────────────────────────────
# 3. Pico de npm run build
# ────────────────────────────────────────────────────────────────────────────
def medir_build_frontend() -> dict:
    """Ejecuta `npm run build` y samplea RSS cada 200 ms."""
    print("[3/3] Ejecutando 'npm run build' en frontend/ (esto tarda 10-60 s)…")
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if npm is None:
        return {"ok": False, "error": "npm no está en PATH."}
    if not (FRONTEND_DIR / "package.json").exists():
        return {"ok": False, "error": f"No existe {FRONTEND_DIR / 'package.json'}."}
    if not (FRONTEND_DIR / "node_modules").exists():
        return {
            "ok": False,
            "error": (
                f"Falta {FRONTEND_DIR / 'node_modules'}. Ejecute 'npm install' "
                "en frontend/ antes de medir el build."
            ),
        }

    t0 = time.monotonic()
    proc = subprocess.Popen(
        [npm, "run", "build"],
        cwd=str(FRONTEND_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=False,
    )

    pico = 0
    muestras = 0
    try:
        while proc.poll() is None:
            rss = sumar_rss_arbol(proc.pid)
            pico = max(pico, rss)
            muestras += 1
            time.sleep(SAMPLE_INTERVAL_S)
        # Última muestra por si el pico ocurrió justo antes de terminar.
        rss = sumar_rss_arbol(proc.pid)
        pico = max(pico, rss)
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=10)

    duracion = round(time.monotonic() - t0, 1)
    if proc.returncode not in (0, None):
        return {
            "ok": False,
            "error": f"'npm run build' terminó con código {proc.returncode}.",
            "duracion_s": duracion,
            "muestras": muestras,
        }

    return {
        "ok": True,
        "pico_bytes": pico,
        "pico_mb": mb(pico),
        "duracion_s": duracion,
        "muestras": muestras,
        "descripcion": (
            "RSS máximo del árbol de procesos de 'npm run build' muestreado "
            f"cada {int(SAMPLE_INTERVAL_S * 1000)} ms; incluye Node + esbuild + Rollup."
        ),
    }


# ────────────────────────────────────────────────────────────────────────────
# Entrada
# ────────────────────────────────────────────────────────────────────────────
def main() -> int:
    uname = platform.uname()
    host = {
        "system": uname.system,
        "release": uname.release,
        "machine": uname.machine,
        "processor": uname.processor,
        "cpu_count": psutil.cpu_count(logical=True),
        "ram_total_mb": mb(psutil.virtual_memory().total),
        "python": sys.version.split()[0],
    }

    resultados = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "host": host,
        "django_reposo": medir_django_reposo(),
        "postgres": medir_postgres(),
        "build_frontend": medir_build_frontend(),
    }

    OUTPUT_JSON.write_text(json.dumps(resultados, indent=2, ensure_ascii=False))

    # Tabla legible
    print()
    print("=" * 68)
    print("Requisitos mínimos de hardware — cifras medidas")
    print("=" * 68)
    print(
        f"Host: {host['system']} {host['release']} · {host['machine']} · "
        f"{host['cpu_count']} vCPU · {host['ram_total_mb']} MB RAM · "
        f"Python {host['python']}"
    )
    print(f"Fecha: {resultados['timestamp']}")
    print("-" * 68)
    print(f"{'Componente':<32}{'Métrica':>18}{'Valor (MB)':>18}")
    print("-" * 68)

    d = resultados["django_reposo"]
    if d.get("ok"):
        print(f"{'Django (runserver, reposo)':<32}{'RSS':>18}{d['rss_mb']:>18}")
    else:
        print(f"{'Django (runserver, reposo)':<32}{'ERROR':>18}{d.get('error', ''):>18}")

    p = resultados["postgres"]
    if p.get("ok"):
        print(f"{'PostgreSQL (todos los procs)':<32}{'RSS suma':>18}{p['rss_total_mb']:>18}")
    else:
        print(f"{'PostgreSQL (todos los procs)':<32}{'ERROR':>18}{p.get('error', ''):>18}")

    b = resultados["build_frontend"]
    if b.get("ok"):
        print(
            f"{'npm run build (pico)':<32}{'RSS pico':>18}{b['pico_mb']:>18}"
            f"    ({b['duracion_s']} s, {b['muestras']} muestras)"
        )
    else:
        print(f"{'npm run build (pico)':<32}{'ERROR':>18}{b.get('error', ''):>18}")

    print("-" * 68)
    print(f"Detalle JSON: {OUTPUT_JSON}")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
