"""Capturas de pantalla para el reporte usando Playwright.
Requiere:
  - Backend Django corriendo en :8000
  - Frontend Vite corriendo en :5173
  - Datos de seed cargados (seed_users + seed_demo)

Uso:
  .venv/Scripts/python.exe scripts/capturar_screenshots.py
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parents[2] / "docs" / "reporte" / "Imagenes" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

BASE = "http://localhost:5173"
ADMIN = ("admin@cyad.uam.mx", "Admin1234!")
PROF = ("profesor@cyad.uam.mx", "Profesor1234!")


def login(page, email, password):
    """Login vía API + inyección de tokens (evita rate limiting de /auth/login)."""
    import json, urllib.request
    body = json.dumps({"email": email, "password": password}).encode()
    req = urllib.request.Request("http://localhost:8000/api/v1/auth/login/", data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        tokens = json.loads(resp.read())
    access = tokens["access"]
    refresh = tokens["refresh"]
    page.goto(BASE, wait_until="domcontentloaded")
    page.evaluate("([a, r]) => { localStorage.setItem('access', a); localStorage.setItem('refresh', r); }", [access, refresh])
    page.reload(wait_until="networkidle")
    page.wait_for_timeout(500)


def goto_authed(page, path):
    """Navega manteniendo la sesión (client-side routing cuando es posible)."""
    page.goto(f"{BASE}{path}", wait_until="networkidle")
    page.wait_for_timeout(1500)


def snap(page, name, full_page=True):
    path = OUT / f"{name}.png"
    page.screenshot(path=str(path), full_page=full_page)
    print(f"  [OK] {path.name}")


def logout(page):
    page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
    page.context.clear_cookies()


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
    page = ctx.new_page()

    print("== Login ==")
    page.goto(f"{BASE}/login", wait_until="networkidle")
    page.wait_for_timeout(500)
    snap(page, "login", full_page=False)

    print("== Público - Explorar ==")
    page.goto(f"{BASE}/", wait_until="networkidle")
    page.wait_for_timeout(1000)
    snap(page, "publico_explorar")

    print("== Docente ==")
    login(page, *PROF)
    page.wait_for_timeout(1500)
    snap(page, "docente_dashboard")

    page.goto(f"{BASE}/profesor/cartas", wait_until="networkidle")
    page.wait_for_timeout(1200)
    snap(page, "docente_cartas_lista")

    page.goto(f"{BASE}/profesor/cartas/nueva", wait_until="networkidle")
    page.wait_for_timeout(1200)
    snap(page, "docente_carta_form")

    page.goto(f"{BASE}/profesor/requisitos/nuevo", wait_until="networkidle")
    page.wait_for_timeout(1200)
    snap(page, "docente_requisito_form")

    page.goto(f"{BASE}/profesor/autoevaluacion", wait_until="networkidle")
    page.wait_for_timeout(1200)
    snap(page, "docente_autoevaluacion")

    logout(page)

    print("== Administrador ==")
    login(page, *ADMIN)
    page.wait_for_timeout(1500)
    snap(page, "admin_dashboard")

    page.goto(f"{BASE}/admin/profesores", wait_until="networkidle")
    page.wait_for_timeout(1200)
    snap(page, "admin_profesores")

    page.goto(f"{BASE}/admin/autoevaluacion", wait_until="networkidle")
    page.wait_for_timeout(1200)
    snap(page, "admin_formulario_builder")

    page.goto(f"{BASE}/admin/reportes", wait_until="networkidle")
    page.wait_for_timeout(1200)
    snap(page, "admin_reportes")

    browser.close()
    print(f"\nCapturas guardadas en: {OUT}")
