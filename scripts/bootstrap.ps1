# scripts/bootstrap.ps1
# Prepara la base de datos y los datos de demo para desarrollo local.
#
# Requiere:
#   - .venv activo en la sesión (backend\.venv\Scripts\Activate.ps1)
#   - Dependencias ya instaladas: pip install -r backend\requirements.txt
#   - backend\.env configurado (copiar de backend\.env.example y ajustar DB_PASSWORD)
#
# Uso:
#   .\scripts\bootstrap.ps1
#
# Este script no arranca el backend ni el frontend; al terminar imprime los
# comandos exactos para hacerlo en dos terminales separadas.

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $repoRoot 'backend'

if (-not (Test-Path (Join-Path $backend 'manage.py'))) {
    Write-Error "No se encontró backend\manage.py; ¿el script fue movido de scripts\?"
    exit 1
}

if (-not (Test-Path (Join-Path $backend '.env'))) {
    Write-Error "Falta backend\.env. Copie backend\.env.example y ajuste DB_PASSWORD antes de correr el bootstrap."
    exit 1
}

Push-Location $backend
try {
    Write-Host "[1/3] Creando base de datos..." -ForegroundColor Cyan
    python scripts\create_db.py

    Write-Host "[2/3] Aplicando migraciones..." -ForegroundColor Cyan
    python manage.py migrate

    Write-Host "[3/3] Cargando datos de demo (usuarios, catalogos, formulario)..." -ForegroundColor Cyan
    python scripts\seed_demo.py

    Write-Host ""
    Write-Host "== Bootstrap completado ==" -ForegroundColor Green
    Write-Host ""
    Write-Host "Siguientes pasos (en dos terminales distintas):" -ForegroundColor Yellow
    Write-Host "  1) Backend:  cd backend; python manage.py runserver 8000"
    Write-Host "  2) Frontend: cd frontend; npm run dev"
    Write-Host ""
    Write-Host "Credenciales de prueba:" -ForegroundColor Yellow
    Write-Host "  ADMIN     admin@cyad.uam.mx      / Admin1234!"
    Write-Host "  PROFESOR  profesor@cyad.uam.mx   / Profesor1234!"
}
finally {
    Pop-Location
}
