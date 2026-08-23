"""Capturas de pantalla para el reporte usando Playwright.

Genera el conjunto completo de capturas referenciadas por el manual de usuario
(``docs/reporte/secciones/11d_manual_usuario.tex``) y por la Sección de
resultados (``docs/reporte/secciones/07_resultados.tex``).

Requisitos:
  - Backend Django corriendo en :8000
  - Frontend Vite corriendo en :5173
  - Datos de seed cargados (``python scripts/seed_users.py`` y
    ``python scripts/seed_demo.py``)

Uso:
  .venv/Scripts/python.exe scripts/capturar_screenshots.py
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parents[2] / "docs" / "reporte" / "Imagenes" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

BASE = "http://localhost:5173"
API = "http://localhost:8000/api/v1"
ADMIN = ("admin@cyad.uam.mx", "Admin1234!")
PROF = ("profesor@cyad.uam.mx", "Profesor1234!")


def login(page, email, password):
    """Login vía API + inyección de tokens (evita rate limiting de /auth/login)."""
    import json
    import urllib.request

    body = json.dumps({"email": email, "password": password}).encode()
    req = urllib.request.Request(
        f"{API}/auth/login/",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        tokens = json.loads(resp.read())
    page.goto(BASE, wait_until="domcontentloaded")
    page.evaluate(
        "([a, r]) => { localStorage.setItem('access', a); localStorage.setItem('refresh', r); }",
        [tokens["access"], tokens["refresh"]],
    )
    page.reload(wait_until="networkidle")
    page.wait_for_timeout(500)


def logout(page):
    page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
    page.context.clear_cookies()


def goto(page, path, wait_ms=1500):
    page.goto(f"{BASE}{path}", wait_until="networkidle")
    page.wait_for_timeout(wait_ms)


def snap(page, name, full_page=True):
    path = OUT / f"{name}.png"
    page.screenshot(path=str(path), full_page=full_page)
    print(f"  [OK] {path.name}")


def click_button_by_text(page, text):
    page.evaluate(
        "(t) => [...document.querySelectorAll('button')].find(b => b.textContent.trim() === t)?.click()",
        text,
    )
    page.wait_for_timeout(600)


def close_dialog(page):
    page.evaluate(
        "() => { const d=document.querySelector('[role=\"dialog\"]');"
        "if(d) [...d.querySelectorAll('button')].find(b => /cancelar|cerrar/i.test(b.textContent))?.click(); }"
    )
    page.wait_for_timeout(300)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
    page = ctx.new_page()

    # ─────────────── Público (sin login) ─────────────────────────
    print("== Público ==")
    goto(page, "/", wait_ms=1000)
    snap(page, "publico_home")

    goto(page, "/publico/explorar/cartas", wait_ms=1500)
    snap(page, "publico_explorar_cartas_inicial")

    # Selecciona un periodo y una licenciatura con documentos publicados.
    # Requiere que el seed haya dejado cartas publicadas en 26-O DCG.
    page.evaluate(
        """() => {
        const sel = document.querySelector('select');
        if (sel) {
          const opt = [...sel.options].find(o => o.text === '26-O');
          if (opt) { sel.value = opt.value; sel.dispatchEvent(new Event('change', {bubbles: true})); }
        }
      }"""
    )
    page.wait_for_timeout(800)
    # Click en la licenciatura "Diseño de la comunicación gráfica"
    page.evaluate(
        """() => {
        const btn = [...document.querySelectorAll('button')].find(b => /Diseño de la comunicación gráfica/i.test(b.textContent));
        btn?.click();
      }"""
    )
    page.wait_for_timeout(1500)
    # Expande la primera UEA disponible
    page.evaluate(
        """() => {
        const btn = [...document.querySelectorAll('button')].find(b => /^\\d{7}\\s/.test(b.textContent.trim()));
        btn?.click();
      }"""
    )
    page.wait_for_timeout(1000)
    snap(page, "publico_explorar_cartas_seleccion")

    # Detalle público de una carta publicada — el id se descubre del listado
    carta_id = page.evaluate(
        """() => {
        const a = document.querySelector('a[href*=\"/publico/cartas/\"]');
        return a ? a.getAttribute('href').split('/').pop() : null;
      }"""
    )
    if carta_id:
        goto(page, f"/publico/cartas/{carta_id}", wait_ms=1500)
        snap(page, "publico_carta")

    # Requisitos — mismo flujo, publicados en 26-P DiPS por el seed
    goto(page, "/publico/explorar/requisitos", wait_ms=1500)
    page.evaluate(
        """() => {
        const sel = document.querySelector('select');
        if (sel) {
          const opt = [...sel.options].find(o => o.text === '26-P');
          if (opt) { sel.value = opt.value; sel.dispatchEvent(new Event('change', {bubbles: true})); }
        }
      }"""
    )
    page.wait_for_timeout(800)
    page.evaluate(
        """() => {
        const btn = [...document.querySelectorAll('button')].find(b => /Diseño de proyectos sustentables/i.test(b.textContent));
        btn?.click();
      }"""
    )
    page.wait_for_timeout(1500)
    page.evaluate(
        """() => {
        const btn = [...document.querySelectorAll('button')].find(b => /^\\d{7}\\s/.test(b.textContent.trim()));
        btn?.click();
      }"""
    )
    page.wait_for_timeout(1000)
    snap(page, "publico_explorar_requisitos_seleccion")

    # ─────────────── Login ────────────────────────────────────────
    print("== Login ==")
    goto(page, "/login", wait_ms=800)
    snap(page, "login", full_page=False)

    # ─────────────── Administrador ────────────────────────────────
    print("== Administrador ==")
    login(page, *ADMIN)

    goto(page, "/admin", wait_ms=2000)
    snap(page, "admin_dashboard")

    # Profesores
    goto(page, "/admin/profesores", wait_ms=1500)
    snap(page, "admin_profesores_lista")
    click_button_by_text(page, "+ Nuevo Profesor")
    snap(page, "admin_profesor_nuevo", full_page=False)
    close_dialog(page)
    # Modal editar (primer botón "Editar")
    page.evaluate(
        "() => [...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'Editar')?.click()"
    )
    page.wait_for_timeout(600)
    snap(page, "admin_profesor_editar", full_page=False)
    close_dialog(page)
    # Modal contraseña
    page.evaluate(
        "() => [...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'Contraseña')?.click()"
    )
    page.wait_for_timeout(600)
    snap(page, "admin_profesor_contrasena", full_page=False)
    close_dialog(page)

    # Catálogos — cada uno con su modal "Nuevo"
    catalogos = [
        ("/admin/catalogos/departamentos", "+ Nuevo", "admin_catalogo_departamento_nuevo"),
        ("/admin/catalogos/licenciaturas", "+ Nueva", "admin_catalogo_licenciatura_nuevo"),
        ("/admin/catalogos/posgrados", "+ Nuevo", "admin_catalogo_posgrado_nuevo"),
        ("/admin/catalogos/areas", "+ Nueva Área", "admin_catalogo_area_nuevo"),
    ]
    for path, btn_text, out_name in catalogos:
        goto(page, path, wait_ms=1000)
        click_button_by_text(page, btn_text)
        snap(page, out_name, full_page=False)
        close_dialog(page)

    # UEA — alta individual + importar CSV
    goto(page, "/admin/catalogos/uea", wait_ms=1500)
    click_button_by_text(page, "+ Nueva UEA")
    snap(page, "admin_catalogo_uea_nuevo", full_page=False)
    close_dialog(page)
    click_button_by_text(page, "Importar CSV")
    snap(page, "admin_catalogo_uea_csv", full_page=False)
    close_dialog(page)

    # Periodos
    goto(page, "/admin/catalogos/periodos", wait_ms=1500)
    click_button_by_text(page, "+ Nuevo")
    snap(page, "admin_catalogo_periodo_nuevo")
    close_dialog(page)

    # Autoevaluación
    goto(page, "/admin/autoevaluacion", wait_ms=1500)
    snap(page, "admin_autoevaluacion_lista")
    click_button_by_text(page, "+ Nuevo Formulario")
    snap(page, "admin_autoevaluacion_nueva", full_page=False)
    close_dialog(page)

    # Constructor de un formulario existente (mayor cantidad de preguntas para las capturas).
    # Se toma el id del primer formulario listado.
    form_id = page.evaluate(
        "() => [...document.querySelectorAll('a[href*=\"/admin/autoevaluacion/\"]')]"
        ".map(a => a.getAttribute('href').match(/autoevaluacion\\/(\\d+)/)?.[1])"
        ".find(Boolean)"
    )
    if form_id:
        goto(page, f"/admin/autoevaluacion/{form_id}", wait_ms=2000)
        snap(page, "admin_autoevaluacion_preguntas", full_page=False)
        click_button_by_text(page, "Niveles de Desempeño")
        page.wait_for_timeout(500)
        snap(page, "admin_autoevaluacion_niveles")
        click_button_by_text(page, "Estadísticas")
        page.wait_for_timeout(1500)
        snap(page, "admin_autoevaluacion_estadisticas")

    # Reportes
    goto(page, "/admin/reportes", wait_ms=1500)
    snap(page, "admin_reportes")

    logout(page)

    # ─────────────── Profesor ─────────────────────────────────────
    print("== Profesor ==")
    login(page, *PROF)

    goto(page, "/profesor", wait_ms=1500)
    snap(page, "docente_dashboard")

    goto(page, "/profesor/cartas/nueva", wait_ms=1500)
    snap(page, "docente_carta_form")

    goto(page, "/profesor/requisitos/nuevo", wait_ms=1500)
    snap(page, "docente_requisito_form")

    goto(page, "/profesor/autoevaluacion", wait_ms=1500)
    # Toma el id del primer formulario disponible
    autoeval_id = page.evaluate(
        "() => [...document.querySelectorAll('a[href*=\"/profesor/autoevaluacion/\"]')]"
        ".map(a => a.getAttribute('href').match(/autoevaluacion\\/(\\d+)/)?.[1])"
        ".find(Boolean)"
    )
    if autoeval_id:
        goto(page, f"/profesor/autoevaluacion/{autoeval_id}", wait_ms=2000)
        snap(page, "docente_autoevaluacion_contestar")

    browser.close()
    print(f"\nCapturas guardadas en: {OUT}")
