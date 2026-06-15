"""Carga idempotente de catálogos institucionales desde CSVs.

Lee `areas.csv`, `licenciaturas.csv`, `posgrados.csv` y `ueas_ejemplo.csv` (en
ese orden) y hace upsert en las tablas `Area`, `Licenciatura`, `Posgrado` y
`UEA`.

CSVs esperados (ver `C:\\Users\\godin\\Documents\\10_2025_Proyectos\\CSV`):

  areas.csv:
      area_id,nombre,descripcion

  licenciaturas.csv:
      licenciatura_id,clave,nombre

  posgrados.csv (opcional):
      clave,nombre

  ueas_ejemplo.csv:
      area_id,clave,nombre,programa_clave,trimestre,tipo,creditos,url

El CSV de UEAs trae una sola columna `programa_clave` con la clave de la
Licenciatura o del Posgrado al que pertenece la UEA; el lookup se hace
contra ambas tablas y debe ser inequívoco (si una misma clave existe en
ambos modelos la fila se rechaza como ambigua).

Uso:
    python manage.py cargar_catalogos_csv
    python manage.py cargar_catalogos_csv --csv-dir /ruta/a/CSV
    python manage.py cargar_catalogos_csv --ueas-csv /ruta/a/otro.csv
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalogos.models import Area, Licenciatura, Posgrado, UEA


DEFAULT_CSV_DIR = Path(r"C:\Users\godin\Documents\10_2025_Proyectos\CSV")


class Command(BaseCommand):
    help = "Carga áreas, licenciaturas, posgrados y UEAs desde los CSVs canónicos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-dir",
            type=Path,
            default=DEFAULT_CSV_DIR,
            help="Directorio que contiene los CSVs (default: %(default)s).",
        )
        parser.add_argument("--areas-csv", type=Path, default=None)
        parser.add_argument("--licenciaturas-csv", type=Path, default=None)
        parser.add_argument("--posgrados-csv", type=Path, default=None)
        parser.add_argument("--ueas-csv", type=Path, default=None)

    def handle(self, *args, **opts):
        csv_dir: Path = opts["csv_dir"]
        areas_csv: Path = opts["areas_csv"] or (csv_dir / "areas.csv")
        lics_csv: Path = opts["licenciaturas_csv"] or (csv_dir / "licenciaturas.csv")
        pos_csv: Path = opts["posgrados_csv"] or (csv_dir / "posgrados.csv")
        ueas_csv: Path = opts["ueas_csv"] or (csv_dir / "ueas_ejemplo.csv")

        for path in (areas_csv, lics_csv, ueas_csv):
            if not path.exists():
                raise CommandError(f"No existe el CSV: {path}")

        with transaction.atomic():
            area_map = self._cargar_areas(areas_csv)
            lic_map = self._cargar_licenciaturas(lics_csv)
            if pos_csv.exists():
                self._cargar_posgrados(pos_csv)
            else:
                self.stdout.write(
                    self.style.WARNING(f"Posgrados: omitido (no existe {pos_csv}).")
                )
            self._cargar_ueas(ueas_csv, area_map, lic_map)

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
                # Defensa: si en algún entorno todavía dice "DPS", renombrar a "DiPS".
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
        """Upsert por `clave`. `orden` se asigna por la posición en el CSV.

        Devuelve {clave: Posgrado}.
        """
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
        lic_map: dict[str, Licenciatura],
    ) -> None:
        """Upsert por `clave`."""
        lic_por_clave = {l.clave: l for l in Licenciatura.objects.all()}
        pos_por_clave = {p.clave: p for p in Posgrado.objects.all()}
        colisiones = set(lic_por_clave) & set(pos_por_clave)
        tipo_map = {
            "OBL": UEA.Tipo.OBLIGATORIA,
            "OPT": UEA.Tipo.OPTATIVA,
        }
        created, updated, errors = 0, 0, []
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

                area_raw = (row.get("area_id") or "").strip()
                area = area_map.get(area_raw)

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
                    clave=clave, defaults=defaults
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

    def _resolver_programa(self, row, lic_por_clave, pos_por_clave, colisiones):
        """Resuelve (licenciatura, posgrado, error) para una fila de UEA.

        Busca `programa_clave` primero en Licenciatura y, si no encuentra, en
        Posgrado. Si la clave existe en ambas tablas se devuelve error de
        ambigüedad.
        """
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
