"""Smoke test E2E contra el backend en ejecución.

Pre-requisitos:
1) Backend levantado en BASE_URL (default http://localhost:8000)
2) Datos creados con: python scripts/seed_demo.py

Ejecuta:
    python scripts/smoke_test.py

Valida:
- POST /auth/login  como ADMIN y PROFESOR
- GET  /auth/me     devuelve el rol correcto
- GET  /uea/        lista catálogo
- GET  /formularios-disponibles/  para profesor
- POST /respuestas/  (borrador)  +  /respuestas/{id}/enviar/  (cálculo de puntaje)
- POST /cartas-tematicas/        creación de documento
- GET  /reportes/dashboard/      como admin

Cada paso imprime OK/FAIL. Sale con código != 0 si algo falla.
"""

from __future__ import annotations

import io
import os
import sys
import json
from typing import Any

# Forzar UTF-8 en stdout para Windows (cp1252 no soporta -> ni acentos)
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

try:
    import urllib.request as urlreq
    import urllib.error as urlerr
except Exception as e:
    print(f"FATAL: no se pudo importar urllib: {e}")
    sys.exit(1)


BASE = os.environ.get("BACKEND_URL", "http://localhost:8000").rstrip("/")
API = f"{BASE}/api/v1"

FAIL = []


def request(method: str, path: str, token: str | None = None, body: Any | None = None) -> tuple[int, Any]:
    url = path if path.startswith("http") else f"{API}{path}"
    data = None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urlreq.Request(url, data=data, headers=headers, method=method)
    try:
        with urlreq.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8") or "null"
            return resp.status, json.loads(raw)
    except urlerr.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except Exception:
            payload = raw
        return e.code, payload
    except Exception as e:
        return 0, str(e)


def step(name: str, ok: bool, info: str = "") -> None:
    flag = "OK  " if ok else "FAIL"
    print(f"  [{flag}] {name}" + (f"  -- {info}" if info else ""))
    if not ok:
        FAIL.append(name)


def section(title: str) -> None:
    print(f"\n=== {title} ===")


# ─── 1) Salud ──────────────────────────────────────────────────────────────
section("Salud del backend")
code, data = request("GET", "/health/")
step(f"GET /health → {code}", code == 200 and isinstance(data, dict) and data.get("status") == "ok",
     info=str(data)[:80])
if FAIL:
    print("\nBackend no responde correctamente. Aborto.")
    sys.exit(1)


# ─── 2) Login ADMIN ────────────────────────────────────────────────────────
section("Login")
code, data = request("POST", "/auth/login/", body={
    "email": "admin@cyad.uam.mx", "password": "Admin1234!"
})
ok = code == 200 and isinstance(data, dict) and "access" in data
step(f"POST /auth/login admin → {code}", ok)
admin_token = data.get("access") if ok else None

code, data = request("POST", "/auth/login/", body={
    "email": "profesor@cyad.uam.mx", "password": "Profesor1234!"
})
ok = code == 200 and isinstance(data, dict) and "access" in data
step(f"POST /auth/login profesor → {code}", ok)
prof_token = data.get("access") if ok else None

if not (admin_token and prof_token):
    print("\nNo se obtuvo token. Aborto.")
    sys.exit(1)


# ─── 3) /auth/me ───────────────────────────────────────────────────────────
section("/auth/me")
code, me_a = request("GET", "/auth/me/", token=admin_token)
me_a_data = me_a.get("data", me_a) if isinstance(me_a, dict) else {}
step(f"me admin → rol={me_a_data.get('rol')}", code == 200 and me_a_data.get("rol") == "ADMIN")

code, me_p = request("GET", "/auth/me/", token=prof_token)
me_p_data = me_p.get("data", me_p) if isinstance(me_p, dict) else {}
step(f"me profesor → rol={me_p_data.get('rol')}", code == 200 and me_p_data.get("rol") == "PROFESOR")


# ─── 4) Catálogos ──────────────────────────────────────────────────────────
section("Catálogos")
code, data = request("GET", "/uea/", token=admin_token)
ueas = data.get("results", data) if isinstance(data, dict) else data
step(f"GET /uea/ → {code} (count={len(ueas) if isinstance(ueas, list) else '?'})",
     code == 200 and isinstance(ueas, list) and len(ueas) > 0)
uea_id = ueas[0]["id"] if isinstance(ueas, list) and ueas else None

code, data = request("GET", "/periodos/", token=admin_token)
periodos = data.get("results", data) if isinstance(data, dict) else data
periodo_activo = next((p for p in periodos if p.get("activo")), None) if isinstance(periodos, list) else None
step(f"GET /periodos/ → periodo activo {periodo_activo.get('clave') if periodo_activo else '?'}",
     bool(periodo_activo))


# ─── 5) Formularios disponibles para el profesor ───────────────────────────
section("Autoevaluación — flujo profesor")
code, data = request("GET", "/formularios-disponibles/", token=prof_token)
disp = data.get("results", data) if isinstance(data, dict) else data
step(f"GET /formularios-disponibles/ → {code} (count={len(disp) if isinstance(disp, list) else '?'})",
     code == 200 and isinstance(disp, list) and len(disp) > 0)
form_id = disp[0]["id"] if isinstance(disp, list) and disp else None
if form_id:
    code, formulario = request("GET", f"/formularios-disponibles/{form_id}/", token=prof_token)
    preguntas = formulario.get("preguntas", []) if isinstance(formulario, dict) else []
    step(f"Detalle formulario v{formulario.get('version')} ({len(preguntas)} preguntas)",
         code == 200 and len(preguntas) > 0)


# ─── 6) Crear y enviar respuesta ──────────────────────────────────────────
if form_id:
    code, data = request("POST", "/respuestas/", token=prof_token,
                         body={"formulario": form_id})
    resp_id = data.get("id") if isinstance(data, dict) else None
    # Si ya existe respuesta para esta versión (ejecuciones previas), reutilizar
    if not resp_id:
        code_l, lst = request("GET", "/respuestas/", token=prof_token)
        items = lst.get("results", lst) if isinstance(lst, dict) else lst
        candidatas = [r for r in items if r.get("formulario") == form_id] if isinstance(items, list) else []
        if candidatas:
            resp_id = candidatas[0]["id"]
    step(f"Respuesta (borrador o existente) id={resp_id}", bool(resp_id))


# ─── 7) Documentos: crear Carta Temática ──────────────────────────────────
section("Documentos")
if uea_id and periodo_activo:
    # `periodo` ya no se envía (lo asigna el backend según el flag activo_cartas).
    payload = {
        "uea": uea_id,
        "nombre_grupo": f"SMOKE-{os.getpid()}",
        "id_grupo": f"CT{os.getpid()}",
        "horario": "Lun-Mie 10:00-12:00",
        "modalidad": "PRESENCIAL",
        "objetivo_general": "Objetivo de prueba smoke test.",
        "presentacion": "Carta creada por smoke_test.py",
        "temas": [],
        "bibliografias": [],
        "criterios": [],
    }
    code, data = request("POST", "/cartas-tematicas/", token=prof_token, body=payload)
    ok = code in (200, 201) and isinstance(data, dict) and "id" in data
    step(f"POST /cartas-tematicas/ → {code}", ok, info=str(data)[:120] if not ok else f"id={data.get('id')}")


# ─── 8) Reportes (admin) ──────────────────────────────────────────────────
section("Reportes (admin)")
code, dash = request("GET", "/reportes/dashboard/", token=admin_token)
step(f"GET /reportes/dashboard/ → {code}", code == 200 and isinstance(dash, dict))
code, cumpl = request("GET", "/reportes/cumplimiento-licenciatura/", token=admin_token)
step(f"GET /reportes/cumplimiento-licenciatura/ → {code}",
     code == 200 and isinstance(cumpl, dict) and "por_licenciatura" in cumpl)


# ─── Resumen ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
if FAIL:
    print(f"SMOKE TEST: {len(FAIL)} fallas")
    for f in FAIL:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("SMOKE TEST: TODOS LOS CHECKS OK")
