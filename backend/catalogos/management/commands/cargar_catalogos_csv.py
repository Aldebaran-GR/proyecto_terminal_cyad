"""Carga idempotente de UEAs (y opcionalmente áreas / licenciaturas / posgrados) desde CSV.

Los catálogos base (departamentos, licenciaturas, posgrados, áreas) viven en el
repo como *fixtures* JSON y se cargan con ``python manage.py loaddata``. Este
comando cubre la carga masiva de UEAs desde los CSV oficiales de coordinación,
que también viven versionados en ``backend/catalogos/fixtures/``:

    - ``ueas_licenciatura.csv``   (~430 filas: DCG, ARQ, DI, DiPS)
    - ``ueas_posgrado.csv``       (~80 filas: PPCDA, PDB, PDEU)

CSV esperado (encabezado):

    clave,nombre,programa_clave,trimestre,tipo,creditos,area_nombre,area_descripcion,url

- ``programa_clave`` se busca en Licenciatura y, si no encuentra, en Posgrado.
  Si la clave existe en ambos modelos la fila se rechaza como ambigua.
- ``area_nombre`` + ``area_descripcion`` se resuelven contra la tabla ``Area``.
  Las áreas oficiales están precargadas por ``areas.json``; si el par no
  existe, la UEA queda con ``area = NULL`` y se reporta como *warning* (nunca
  se crea un área nueva desde este comando).

Opcionalmente, también acepta ``areas.csv``, ``licenciaturas.csv`` y
``posgrados.csv`` para escenarios ad-hoc en los que coordinación entregue esos
catálogos como CSV en vez de JSON.

Uso típico (desde ``backend/``):

    python manage.py cargar_catalogos_csv \\
        --ueas-csv catalogos/fixtures/ueas_licenciatura.csv
    python manage.py cargar_catalogos_csv \\
        --ueas-csv catalogos/fixtures/ueas_posgrado.csv
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalogos.models import Area, Licenciatura, Posgrado, UEA


# Directorio versionado donde viven los CSV oficiales dentro del repo.
DEFAULT_CSV_DIR = Path(__file__).resolve().parents[2] / "catalogos" / "fixtures"


class Command(BaseCommand):
    help = "Carga UEAs (y opcionalmente áreas/licenciaturas/posgrados) desde CSV."

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-dir",
            type=Path,
            default=DEFAULT_CSV_DIR,
            help="Directorio con CSVs opcionales (default: %(default)s).",
        )
        parser.add_argument("--areas-csv", type=Path, default=None)
        parser.add_argument("--licenciaturas-csv", type=Path, default=None)
        parser.add_argument("--posgrados-csv", type=Path, default=None)
        parser.add_argument(
            "--ueas-csv",
            type=Path,
            default=None,
            help="CSV de UEAs a cargar. Puede repetirse la invocación para varios.",
        )

    def handle(self, *args, **opts):
        csv_dir: Path = opts["csv_dir"]
        areas_csv: Path | None = opts["areas_csv"]
        lics_csv: Path | None = opts["licenciaturas_csv"]
        pos_csv: Path | None = opts["posgrados_csv"]
        ueas_csv: Path | None = opts["ueas_csv"]

        # Descubrimiento por convención dentro de csv_dir: si no se pasa la ruta
        # explícita y existe el archivo en el directorio, se usa. Esto mantiene
        # la compatibilidad con el flujo histórico (un solo ``csv_dir`` con los
        # cuatro archivos) y con las llamadas explícitas por ``--ueas-csv``.
        if areas_csv is None:
            candidato = csv_dir / "areas.csv"
            if candidato.exists():
                areas_csv = candidato
        if lics_csv is None:
            candidato = csv_dir / "licenciaturas.csv"
            if candidato.exists():
                lics_csv = candidato
        if pos_csv is None:
            candidato = csv_dir / "posgrados.csv"
            if candidato.exists():
                pos_csv = candidato
        if ueas_csv is None:
            candidato = csv_dir / "ueas_ejemplo.csv"
            if candidato.exists():
                ueas_csv = candidato

        if not any([areas_csv, lics_csv, pos_csv, ueas_csv]):
            raise CommandError(
                "Nada que hacer: pase al menos --ueas-csv "
                "(o --areas-csv / --licenciaturas-csv / --posgrados-csv), "
                f"o coloque los CSV convencionales dentro de {csv_dir}."
            )

        with transaction.atomic():
            area_map: dict[str, Area] = {}
            if areas_csv:
                if not areas_csv.exists():
                    raise CommandError(f"No existe el CSV: {areas_csv}")
                area_map = self._cargar_areas(areas_csv)

            if lics_csv:
                if not lics_csv.exists():
                    raise CommandError(f"No existe el CSV: {lics_csv}")
                self._cargar_licenciaturas(lics_csv)

            if pos_csv:
                if not pos_csv.exists():
                    raise CommandError(f"No existe el CSV: {pos_csv}")
                self._cargar_posgrados(pos_csv)

            if ueas_csv:
                if not ueas_csv.exists():
                    raise CommandError(f"No existe el CSV: {ueas_csv}")
                self._cargar_ueas(ueas_csv, area_map)

    # ── Áreas ────────────────────────────────────────────────────────────
    def _cargar_areas(self, path: Path) -> dict[str, Area]:
        """Upsert por (nombre, descripcion). Devuelve {area_id_csv: Area}."""
        mapping: dict[str, Area] = {}
        created, updated = 0, 0
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                csv_id = (row.get("area_id") or "").strip()
                nombre = (row.get("nombre") or "").strip()
                descripcion = (row.get("descripcion") or "").strip()
                if not nombre:
                    continue
                obj, was_created = Area.objects.update_or_create(
                    nombre=nombre,
                    descripcion=descripcion,
                    defaults={"estado": True},
                )
                if csv_id:
                    mapping[csv_id] = obj
                created += int(was_created)
                updated += int(not was_created)
        self.stdout.write(
            self.style.SUCCESS(
                f"Áreas: {created} creadas, {updated} actualizadas "
                f"({len(mapping)} con id_csv)."
            )
        )
        return mapping

    # ── Licenciaturas ────────────────────────────────────────────────────
    def _cargar_licenciaturas(self, path: Path) -> dict[str, Licenciatura]:
        """Upsert por `clave`. Devuelve {licenciatura_id_csv: Licenciatura}."""
        # Defensa: renombra cualquier fila legada DPS → DiPS antes del upsert.
        Licenciatura.objects.filter(clave="DPS").update(clave="DiPS")
        mapping: dict[str, Licenciatura] = {}
        created, updated = 0, 0
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                csv_id = (row.get("licenciatura_id") or "").strip()
                clave = (row.get("clave") or "").strip()
                nombre = (row.get("nombre") or "").strip()
                if not (clave and nombre):
                    continue
                if clave == "DPS":
                    clave = "DiPS"
                orden = int(csv_id) if csv_id.isdigit() else 0
                obj, was_created = Licenciatura.objects.update_or_create(
                    clave=clave,
                    defaults={"nombre": nombre, "orden": orden, "estado": True},
                )
                if csv_id:
                    mapping[csv_id] = obj
                created += int(was_created)
                updated += int(not was_created)
        self.stdout.write(
            self.style.SUCCESS(
                f"Licenciaturas: {created} creadas, {updated} actualizadas."
            )
        )
        return mapping

    # ── Posgrados ────────────────────────────────────────────────────────
    def _cargar_posgrados(self, path: Path) -> dict[str, Posgrado]:
        """Upsert por `clave`. `orden` se asigna por la posición en el CSV."""
        mapping: dict[str, Posgrado] = {}
        created, updated = 0, 0
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for orden, row in enumerate(reader, start=1):
                clave = (row.get("clave") or "").strip()
                nombre = (row.get("nombre") or "").strip()
                if not (clave and nombre):
                    continue
                obj, was_created = Posgrado.objects.update_or_create(
                    clave=clave,
                    defaults={"nombre": nombre, "orden": orden, "estado": True},
                )
                mapping[clave] = obj
                created += int(was_created)
                updated += int(not was_created)
        self.stdout.write(
            self.style.SUCCESS(
                f"Posgrados: {created} creados, {updated} actualizados."
            )
        )
        return mapping

    # ── UEAs ─────────────────────────────────────────────────────────────
    def _cargar_ueas(
        self,
        path: Path,
        area_map: dict[str, Area],
    ) -> None:
        """Upsert por (clave, programa)."""
        lic_por_clave = {l.clave: l for l in Licenciatura.objects.all()}
        pos_por_clave = {p.clave: p for p in Posgrado.objects.all()}
        colisiones = set(lic_por_clave) & set(pos_por_clave)
        # Cache de áreas: clave = (nombre.lower(), descripcion.lower())
        area_por_par = {
            (a.nombre.strip().lower(), a.descripcion.strip().lower()): a
            for a in Area.objects.all()
        }
        tipo_map = {
            "OBL": UEA.Tipo.OBLIGATORIA,
            "OPT": UEA.Tipo.OPTATIVA,
        }
        created, updated, errors, sin_area = 0, 0, [], set()
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, start=2):
                clave = (row.get("clave") or "").strip()
                nombre = (row.get("nombre") or "").strip()
                if not (clave and nombre):
                    errors.append(f"Fila {i}: falta clave o nombre.")
                    continue

                licenciatura, posgrado, error = self._resolver_programa(
                    row, lic_por_clave, pos_por_clave, colisiones
                )
                if error:
                    errors.append(f"Fila {i}: {error}")
                    continue

                # Resolución de área: primero por (nombre, descripcion), y como
                # fallback por area_id (compatibilidad con CSVs históricos).
                area = self._resolver_area(row, area_por_par, area_map, sin_area)

                creditos_raw = (row.get("creditos") or "").strip()
                try:
                    creditos = int(creditos_raw) if creditos_raw else None
                except ValueError:
                    creditos = None

                tipo_raw = (row.get("tipo") or "OBL").strip().upper()
                tipo = tipo_map.get(tipo_raw, UEA.Tipo.OTRO)

                defaults = {
                    "nombre": nombre,
                    "licenciatura": licenciatura,
                    "posgrado": posgrado,
                    "area": area,
                    "trimestre": (row.get("trimestre") or "").strip(),
                    "tipo": tipo,
                    "creditos": creditos,
                    "liga": (row.get("url") or "").strip(),
                    "estado": True,
                }
                _, was_created = UEA.objects.update_or_create(
                    clave=clave, licenciatura=licenciatura, posgrado=posgrado,
                    defaults=defaults,
                )
                created += int(was_created)
                updated += int(not was_created)

        self.stdout.write(
            self.style.SUCCESS(
                f"UEAs: {created} creadas, {updated} actualizadas, "
                f"{len(errors)} errores."
            )
        )
        for err in errors:
            self.stdout.write(self.style.WARNING(f"  · {err}"))
        for par in sorted(sin_area):
            self.stdout.write(
                self.style.WARNING(
                    f"  · Área no encontrada: {par!r} — UEAs afectadas quedaron sin área."
                )
            )

    def _resolver_area(self, row, area_por_par, area_map, sin_area):
        nombre = (row.get("area_nombre") or "").strip()
        descripcion = (row.get("area_descripcion") or "").strip()
        if nombre:
            area = area_por_par.get((nombre.lower(), descripcion.lower()))
            if area is None:
                sin_area.add((nombre, descripcion))
            return area
        # Fallback histórico: area_id numérico contra el mapping construido
        # por --areas-csv en la misma invocación.
        area_raw = (row.get("area_id") or "").strip()
        return area_map.get(area_raw)

    def _resolver_programa(self, row, lic_por_clave, pos_por_clave, colisiones):
        """Resuelve (licenciatura, posgrado, error) para una fila de UEA."""
        programa_clave = (row.get("programa_clave") or "").strip()
        if not programa_clave:
            return None, None, "programa_clave es obligatoria."
        if programa_clave in colisiones:
            return None, None, (
                f"clave '{programa_clave}' es ambigua "
                "(existe en Licenciatura y Posgrado)."
            )
        licenciatura = lic_por_clave.get(programa_clave)
        if licenciatura:
            return licenciatura, None, None
        posgrado = pos_por_clave.get(programa_clave)
        if posgrado:
            return None, posgrado, None
        return None, None, (
            f"programa_clave '{programa_clave}' no corresponde "
            "a ninguna Licenciatura ni Posgrado."
        )
