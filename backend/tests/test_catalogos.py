"""Tests de catálogos institucionales — M2."""

import io
import pytest
from rest_framework.test import APIClient

from accounts.models import Usuario
from catalogos.models import Area, Departamento, Licenciatura, Periodo, Posgrado, UEA


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def admin(db):
    return Usuario.objects.create_user(
        email="admin2@cyad.uam.mx", nombre="Admin2", password="Admin1234!",
        rol=Usuario.Rol.ADMIN, is_staff=True, is_superuser=True,
    )


@pytest.fixture
def profesor(db):
    return Usuario.objects.create_user(
        email="prof2@cyad.uam.mx", nombre="Prof2", password="Profesor1234!",
        rol=Usuario.Rol.PROFESOR,
    )


def auth(client, email, password):
    r = client.post("/api/v1/auth/login/", {"email": email, "password": password}, format="json")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")


@pytest.fixture
def depto(db):
    return Departamento.objects.create(clave="EDT", nombre="Evaluación del Diseño en el Tiempo")


@pytest.fixture
def licenciatura(db, depto):
    return Licenciatura.objects.create(clave="DI", nombre="Diseño Industrial", departamento=depto)


class TestDepartamentos:
    def test_lista_autenticado(self, client, depto, profesor):
        auth(client, "prof2@cyad.uam.mx", "Profesor1234!")
        r = client.get("/api/v1/departamentos/")
        assert r.status_code == 200
        assert r.data["count"] >= 1

    def test_crear_solo_admin(self, client, admin):
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        r = client.post("/api/v1/departamentos/", {"clave": "NUEVO", "nombre": "Nuevo Depto"}, format="json")
        assert r.status_code == 201

    def test_crear_bloqueado_profesor(self, client, profesor):
        auth(client, "prof2@cyad.uam.mx", "Profesor1234!")
        r = client.post("/api/v1/departamentos/", {"clave": "NUEVO", "nombre": "Nuevo"}, format="json")
        assert r.status_code == 403

    def test_clave_unica(self, client, admin, depto):
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        r = client.post("/api/v1/departamentos/", {"clave": "EDT", "nombre": "Duplicado"}, format="json")
        assert r.status_code == 400


class TestLicenciaturas:
    def test_lista(self, client, licenciatura, profesor):
        auth(client, "prof2@cyad.uam.mx", "Profesor1234!")
        r = client.get("/api/v1/licenciaturas/")
        assert r.status_code == 200
        assert r.data["count"] >= 1

    def test_crear_admin(self, client, admin, depto):
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        r = client.post(
            "/api/v1/licenciaturas/",
            {"clave": "ARQ", "nombre": "Arquitectura", "departamento": depto.id},
            format="json",
        )
        assert r.status_code == 201
        assert r.data["departamento_nombre"] == depto.nombre


class TestPosgrado:
    def test_lista(self, client, profesor, db):
        Posgrado.objects.create(clave="PDB", nombre="Posgrado en Diseño Bioclimático")
        auth(client, "prof2@cyad.uam.mx", "Profesor1234!")
        r = client.get("/api/v1/posgrados/")
        assert r.status_code == 200
        assert r.data["count"] >= 1

    def test_crear_admin(self, client, admin, depto):
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        r = client.post(
            "/api/v1/posgrados/",
            {"clave": "PDEU", "nombre": "Posgrado en Diseño de Estudios Urbanos", "departamento": depto.id},
            format="json",
        )
        assert r.status_code == 201
        assert r.data["departamento_nombre"] == depto.nombre

    def test_crear_bloqueado_profesor(self, client, profesor):
        auth(client, "prof2@cyad.uam.mx", "Profesor1234!")
        r = client.post("/api/v1/posgrados/", {"clave": "PX", "nombre": "Posgrado X"}, format="json")
        assert r.status_code == 403


class TestPeriodos:
    def test_solo_un_activo_por_recurso(self, client, admin, db):
        """Al activar el mismo recurso en dos periodos, el segundo apaga al primero."""
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        p1 = client.post("/api/v1/periodos/", {
            "clave": "26-I", "fecha_inicio": "2026-01-01", "fecha_fin": "2026-04-30",
            "activo_cartas": True, "activo_requisitos": True, "activo_autoevaluacion": True,
        }, format="json")
        p2 = client.post("/api/v1/periodos/", {
            "clave": "26-P", "fecha_inicio": "2026-05-01", "fecha_fin": "2026-08-31",
            "activo_cartas": True, "activo_requisitos": True, "activo_autoevaluacion": True,
        }, format="json")
        assert p1.status_code == 201
        assert p2.status_code == 201
        from catalogos.models import Periodo
        # Exactamente un periodo activo por cada recurso, no globalmente.
        assert Periodo.objects.filter(activo_cartas=True).count() == 1
        assert Periodo.objects.filter(activo_requisitos=True).count() == 1
        assert Periodo.objects.filter(activo_autoevaluacion=True).count() == 1
        # `activo` legado sigue siendo OR de los tres → solo 1 periodo lo tiene.
        assert Periodo.objects.filter(activo=True).count() == 1

    def test_publico_licenciaturas_sin_auth(self, client, db):
        """GET /publico/licenciaturas/ funciona sin token."""
        from catalogos.models import Licenciatura
        Licenciatura.objects.create(clave="ARQ-X", nombre="Arq Test", estado=True)
        # APIClient sin auth
        from rest_framework.test import APIClient
        r = APIClient().get("/api/v1/publico/licenciaturas/")
        assert r.status_code == 200
        nombres = [l["nombre"] for l in r.data]
        assert "Arq Test" in nombres

    def test_publico_uea_filtrada_por_lic(self, client, db):
        """GET /publico/uea/?licenciatura=ID solo regresa las de esa lic."""
        from catalogos.models import Licenciatura, UEA
        lic_a = Licenciatura.objects.create(clave="LA", nombre="Lic A", estado=True)
        lic_b = Licenciatura.objects.create(clave="LB", nombre="Lic B", estado=True)
        UEA.objects.create(clave="UA-1", nombre="UEA A1", licenciatura=lic_a)
        UEA.objects.create(clave="UB-1", nombre="UEA B1", licenciatura=lic_b)
        from rest_framework.test import APIClient
        r = APIClient().get(f"/api/v1/publico/uea/?licenciatura={lic_a.id}")
        assert r.status_code == 200
        claves = [u["clave"] for u in r.data]
        assert "UA-1" in claves
        assert "UB-1" not in claves

    def test_activos_separados_por_recurso(self, client, admin, db):
        """26-P puede ser activo para Requisitos/AE y 26-O para Cartas al mismo tiempo."""
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        p_actual = client.post("/api/v1/periodos/", {
            "clave": "26-P", "fecha_inicio": "2026-05-01", "fecha_fin": "2026-08-31",
            "activo_requisitos": True, "activo_autoevaluacion": True,
        }, format="json")
        p_siguiente = client.post("/api/v1/periodos/", {
            "clave": "26-O", "fecha_inicio": "2026-09-01", "fecha_fin": "2026-12-31",
            "activo_cartas": True,
        }, format="json")
        assert p_actual.status_code == 201
        assert p_siguiente.status_code == 201
        r = client.get("/api/v1/periodos/activos/")
        assert r.status_code == 200
        assert r.data["cartas"]["clave"] == "26-O"
        assert r.data["requisitos"]["clave"] == "26-P"
        assert r.data["autoevaluacion"]["clave"] == "26-P"

    def test_fecha_fin_anterior_inicio(self, client, admin, db):
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        r = client.post("/api/v1/periodos/", {
            "clave": "XX-I", "fecha_inicio": "2026-04-30", "fecha_fin": "2026-01-01", "activo": False
        }, format="json")
        assert r.status_code == 400

    def test_eliminar_periodo_activo_bloqueado(self, client, admin, db):
        """Un periodo activo para algún recurso no puede ser eliminado."""
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        from catalogos.models import Periodo
        p = Periodo.objects.create(
            clave="DEL-A", fecha_inicio="2026-01-01", fecha_fin="2026-04-30",
            activo_cartas=True,
        )
        preview = client.get(f"/api/v1/periodos/{p.id}/preview-eliminacion/")
        assert preview.status_code == 200
        assert preview.data["puede_eliminar"] is False
        r = client.delete(f"/api/v1/periodos/{p.id}/")
        assert r.status_code == 400
        assert Periodo.objects.filter(pk=p.id).exists()

    def test_eliminar_periodo_inactivo_en_cascada(self, client, admin, db):
        """Un periodo inactivo se elimina junto con sus cartas/requisitos/formularios/respuestas."""
        from accounts.models import Profesor, Usuario
        from autoevaluacion.models import Formulario, Respuesta
        from catalogos.models import (
            Departamento, Licenciatura, Periodo, UEA,
        )
        from documentos.models import CartaTematica, RequisitoRecuperacion

        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        # Catálogos mínimos
        depto = Departamento.objects.create(clave="DLT", nombre="Del Test")
        lic = Licenciatura.objects.create(clave="DLTL", nombre="DelLic", departamento=depto)
        uea = UEA.objects.create(clave="DELUEA", nombre="UEA Del", licenciatura=lic)
        # Periodo INACTIVO (ningún flag prendido)
        p_old = Periodo.objects.create(
            clave="DEL-OLD", fecha_inicio="2025-01-01", fecha_fin="2025-04-30",
        )
        # Periodo independiente para verificar que no se borra
        p_otro = Periodo.objects.create(
            clave="DEL-OTRO", fecha_inicio="2024-01-01", fecha_fin="2024-04-30",
        )
        u_admin = Usuario.objects.get(email="admin2@cyad.uam.mx")
        # Profesor + perfil
        u_prof = Usuario.objects.create_user(
            email="pdel@uam.mx", nombre="P Del", password="Profesor1234!",
            rol=Usuario.Rol.PROFESOR,
        )
        prof = Profesor.objects.create(
            usuario=u_prof, nombre_completo="P Del",
            correo_institucional="pdel@uam.mx", departamento=depto,
        )
        # Documentos en p_old
        CartaTematica.objects.create(
            profesor=prof, uea=uea, periodo=p_old,
            nombre_grupo="G", id_grupo="DEL-G1", horario="Lun 9-11",
        )
        RequisitoRecuperacion.objects.create(
            profesor=prof, uea=uea, periodo=p_old,
            nombre_grupo="G", id_grupo="DEL-R1", horario="Lun 9-11",
        )
        # Formulario en p_old + respuesta del profesor
        form = Formulario.objects.create(
            titulo="F Del", periodo=p_old, created_by=u_admin,
        )
        Respuesta.objects.create(formulario=form, profesor=prof, version_formulario=1)
        # Documento en p_otro (no debe verse afectado)
        CartaTematica.objects.create(
            profesor=prof, uea=uea, periodo=p_otro,
            nombre_grupo="G", id_grupo="DEL-OTRO-G1", horario="Lun 9-11",
        )

        # Preview
        preview = client.get(f"/api/v1/periodos/{p_old.id}/preview-eliminacion/")
        assert preview.status_code == 200
        assert preview.data["puede_eliminar"] is True
        dep = preview.data["dependencias"]
        assert dep["cartas_tematicas"] == 1
        assert dep["requisitos_recuperacion"] == 1
        assert dep["formularios_autoevaluacion"] == 1
        assert dep["respuestas_autoevaluacion"] == 1

        # Eliminar
        r = client.delete(f"/api/v1/periodos/{p_old.id}/")
        assert r.status_code in (200, 204), r.data
        # El periodo se fue + sus documentos / formularios / respuestas
        assert not Periodo.objects.filter(pk=p_old.id).exists()
        assert CartaTematica.objects.filter(periodo_id=p_old.id).count() == 0
        assert RequisitoRecuperacion.objects.filter(periodo_id=p_old.id).count() == 0
        assert Formulario.objects.filter(periodo_id=p_old.id).count() == 0
        # El otro periodo y su carta siguen intactos
        assert Periodo.objects.filter(pk=p_otro.id).exists()
        assert CartaTematica.objects.filter(periodo_id=p_otro.id).count() == 1


class TestUEA:
    def test_lista_con_filtro(self, client, profesor, licenciatura):
        auth(client, "prof2@cyad.uam.mx", "Profesor1234!")
        UEA.objects.create(clave="1400001", nombre="Taller I", licenciatura=licenciatura, tipo="OBL")
        r = client.get(f"/api/v1/uea/?licenciatura={licenciatura.id}")
        assert r.status_code == 200
        assert r.data["count"] == 1

    def test_import_csv(self, client, admin, licenciatura):
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        csv_content = (
            "clave,nombre,programa_clave,trimestre,tipo,creditos,area_nombre,area_descripcion\n"
            "9900001,UEA CSV Test,DI,3,OBL,8,Licenciatura,Licenciatura\n"
            "9900002,UEA CSV Test 2,DI,4,OBL,6,Licenciatura,Licenciatura\n"
        )
        csv_file = io.BytesIO(csv_content.encode("utf-8"))
        csv_file.name = "test.csv"
        r = client.post("/api/v1/uea/import-csv/", {"file": csv_file}, format="multipart")
        assert r.status_code == 200
        assert r.data["created"] == 2
        assert UEA.objects.filter(clave__startswith="9900").count() == 2
        # El área se creó por upsert y quedó ligada a las UEAs.
        uea = UEA.objects.get(clave="9900001")
        assert uea.area is not None
        assert uea.area.nombre == "Licenciatura"

    def test_import_csv_programa_no_existe(self, client, admin, db):
        """Fila con programa_clave que no existe en ninguna tabla -> error."""
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        csv_content = (
            "clave,nombre,programa_clave,trimestre,tipo,creditos\n"
            "9910001,UEA Mala,INVALIDA,1,OBL,4\n"
        )
        csv_file = io.BytesIO(csv_content.encode("utf-8"))
        csv_file.name = "bad.csv"
        r = client.post("/api/v1/uea/import-csv/", {"file": csv_file}, format="multipart")
        assert r.status_code == 200
        assert len(r.data["errors"]) == 1
        assert "INVALIDA" in r.data["errors"][0]
        assert r.data["created"] == 0
        assert not UEA.objects.filter(clave="9910001").exists()

    def test_trimestre_acepta_rango_romano(self, client, admin, licenciatura):
        """trimestre es CharField — acepta rangos romanos para optativas."""
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        r = client.post("/api/v1/uea/", {
            "clave": "1441001",
            "nombre": "Temas Selectos Disciplinares I",
            "licenciatura": licenciatura.id,
            "trimestre": "VII-XII",
            "tipo": "OPT",
        }, format="json")
        assert r.status_code == 201, r.data
        assert UEA.objects.get(clave="1441001").trimestre == "VII-XII"

    def test_uea_requiere_un_programa(self, client, admin, licenciatura):
        """Una UEA debe tener licenciatura XOR posgrado: ninguno o ambos -> 400."""
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        # Ninguno de los dos.
        r_ninguno = client.post("/api/v1/uea/", {
            "clave": "9920001", "nombre": "Sin programa",
        }, format="json")
        assert r_ninguno.status_code == 400

        # Ambos a la vez.
        posgrado = Posgrado.objects.create(clave="PX", nombre="Posgrado X")
        r_ambos = client.post("/api/v1/uea/", {
            "clave": "9920002", "nombre": "Con ambos",
            "licenciatura": licenciatura.id, "posgrado": posgrado.id,
        }, format="json")
        assert r_ambos.status_code == 400

    def test_uea_con_posgrado(self, client, admin):
        """Una UEA puede pertenecer solo a un Posgrado (sin licenciatura)."""
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        posgrado = Posgrado.objects.create(clave="PY", nombre="Posgrado Y")
        r = client.post("/api/v1/uea/", {
            "clave": "9920003", "nombre": "UEA de Posgrado",
            "posgrado": posgrado.id,
        }, format="json")
        assert r.status_code == 201, r.data
        uea = UEA.objects.get(clave="9920003")
        assert uea.licenciatura is None
        assert uea.posgrado_id == posgrado.id

    def test_import_csv_posgrado(self, client, admin, db):
        """El CSV resuelve programa_clave contra Posgrado cuando la clave existe ahí."""
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        Posgrado.objects.create(clave="PDB", nombre="Posgrado en Diseño Bioclimático")
        csv_content = (
            "clave,nombre,programa_clave,trimestre,tipo,creditos\n"
            "9900010,UEA Posgrado CSV,PDB,1,OBL,9\n"
        )
        csv_file = io.BytesIO(csv_content.encode("utf-8"))
        csv_file.name = "test_pos.csv"
        r = client.post("/api/v1/uea/import-csv/", {"file": csv_file}, format="multipart")
        assert r.status_code == 200, r.data
        assert r.data["created"] == 1
        uea = UEA.objects.get(clave="9900010")
        assert uea.posgrado is not None
        assert uea.posgrado.clave == "PDB"
        assert uea.licenciatura is None

    def test_import_csv_mezcla_licenciatura_y_posgrado(self, client, admin, licenciatura):
        """Un mismo CSV puede traer filas de licenciatura y posgrado mezcladas."""
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        Posgrado.objects.create(clave="PDB", nombre="Posgrado en Diseño Bioclimático")
        csv_content = (
            "clave,nombre,programa_clave,trimestre,tipo,creditos\n"
            "9900020,UEA de Lic,DI,3,OBL,8\n"
            "9900021,UEA de Pos,PDB,1,OBL,9\n"
        )
        csv_file = io.BytesIO(csv_content.encode("utf-8"))
        csv_file.name = "mixto.csv"
        r = client.post("/api/v1/uea/import-csv/", {"file": csv_file}, format="multipart")
        assert r.status_code == 200, r.data
        assert r.data["created"] == 2
        assert r.data["errors"] == []
        u_lic = UEA.objects.get(clave="9900020")
        assert u_lic.licenciatura_id == licenciatura.id and u_lic.posgrado is None
        u_pos = UEA.objects.get(clave="9900021")
        assert u_pos.posgrado.clave == "PDB" and u_pos.licenciatura is None

    def test_import_csv_clave_ambigua(self, client, admin, db):
        """Si la misma clave existe en Licenciatura y Posgrado, la fila se rechaza."""
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        Licenciatura.objects.create(clave="XYZ", nombre="Lic XYZ")
        Posgrado.objects.create(clave="XYZ", nombre="Pos XYZ")
        csv_content = (
            "clave,nombre,programa_clave,trimestre,tipo,creditos\n"
            "9900030,UEA Ambigua,XYZ,1,OBL,4\n"
        )
        csv_file = io.BytesIO(csv_content.encode("utf-8"))
        csv_file.name = "amb.csv"
        r = client.post("/api/v1/uea/import-csv/", {"file": csv_file}, format="multipart")
        assert r.status_code == 200, r.data
        assert r.data["created"] == 0
        assert len(r.data["errors"]) == 1
        assert "ambigua" in r.data["errors"][0].lower()
        assert not UEA.objects.filter(clave="9900030").exists()

    def test_import_csv_falta_programa_clave(self, client, admin, db):
        """Si el header no incluye programa_clave, 400 con mensaje claro."""
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        csv_content = (
            "clave,nombre,trimestre,tipo,creditos\n"
            "9900040,Sin programa,1,OBL,4\n"
        )
        csv_file = io.BytesIO(csv_content.encode("utf-8"))
        csv_file.name = "sin_programa.csv"
        r = client.post("/api/v1/uea/import-csv/", {"file": csv_file}, format="multipart")
        assert r.status_code == 400
        assert "programa_clave" in r.data["errors"]["file"]


class TestArea:
    def test_lista(self, client, profesor, db):
        Area.objects.create(nombre="Licenciatura", descripcion="Licenciatura")
        auth(client, "prof2@cyad.uam.mx", "Profesor1234!")
        r = client.get("/api/v1/areas/")
        assert r.status_code == 200
        assert r.data["count"] >= 1

    def test_crear_admin(self, client, admin):
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        r = client.post("/api/v1/areas/", {
            "nombre": "Optativas de Extensión Divisional",
            "descripcion": "Optativas Interdisciplinares",
        }, format="json")
        assert r.status_code == 201
        assert r.data["nombre"] == "Optativas de Extensión Divisional"

    def test_unique_together(self, client, admin):
        """No se pueden duplicar pares (nombre, descripcion)."""
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        payload = {"nombre": "A", "descripcion": "B"}
        assert client.post("/api/v1/areas/", payload, format="json").status_code == 201
        r2 = client.post("/api/v1/areas/", payload, format="json")
        assert r2.status_code == 400

    def test_crear_bloqueado_profesor(self, client, profesor):
        auth(client, "prof2@cyad.uam.mx", "Profesor1234!")
        r = client.post("/api/v1/areas/", {"nombre": "X", "descripcion": "Y"}, format="json")
        assert r.status_code == 403


class TestCargarCatalogosCsv:
    """El management command carga los 3 CSVs de forma idempotente."""

    def _escribir_csvs(self, tmp_path):
        (tmp_path / "areas.csv").write_text(
            "area_id,nombre,descripcion\n"
            "1,Licenciatura,Licenciatura\n"
            "2,Optativas,Disciplinares\n",
            encoding="utf-8",
        )
        (tmp_path / "licenciaturas.csv").write_text(
            "licenciatura_id,clave,nombre\n"
            "1,DCG,Diseño de la comunicación gráfica\n"
            "2,ARQ,Arquitectura\n"
            "3,DI,Diseño industrial\n"
            "4,DiPS,Diseño de proyectos sustentables\n",
            encoding="utf-8",
        )
        (tmp_path / "ueas_ejemplo.csv").write_text(
            "area_id,clave,nombre,programa_clave,trimestre,tipo,creditos,url\n"
            "1,1440001,UEA Obligatoria,DiPS,3,OBL,9,\n"
            "2,1441001,UEA Optativa Rango,DiPS,VII-XII,OPT,,\n",
            encoding="utf-8",
        )

    def test_carga_idempotente(self, db, tmp_path):
        from django.core.management import call_command

        self._escribir_csvs(tmp_path)
        call_command("cargar_catalogos_csv", csv_dir=tmp_path)

        assert Area.objects.count() == 2
        assert list(
            Licenciatura.objects.order_by("orden").values_list("clave", flat=True)
        ) == ["DCG", "ARQ", "DI", "DiPS"]
        assert UEA.objects.count() == 2
        opt = UEA.objects.get(clave="1441001")
        assert opt.trimestre == "VII-XII"
        assert opt.tipo == "OPT"

        # Segunda corrida no duplica.
        call_command("cargar_catalogos_csv", csv_dir=tmp_path)
        assert Area.objects.count() == 2
        assert Licenciatura.objects.count() == 4
        assert UEA.objects.count() == 2

    def test_renombra_dps_a_dips(self, db, tmp_path):
        """Si existe Licenciatura(clave='DPS') previa, se renombra a 'DiPS'."""
        from django.core.management import call_command

        Licenciatura.objects.create(clave="DPS", nombre="Vieja DPS", orden=99)
        self._escribir_csvs(tmp_path)
        call_command("cargar_catalogos_csv", csv_dir=tmp_path)

        assert not Licenciatura.objects.filter(clave="DPS").exists()
        dips = Licenciatura.objects.get(clave="DiPS")
        assert dips.orden == 4

    def test_carga_posgrados_y_uea_posgrado(self, db, tmp_path):
        """posgrados.csv es opcional; si existe, se cargan y un solo CSV de UEAs mezcla licenciatura/posgrado."""
        from django.core.management import call_command

        self._escribir_csvs(tmp_path)
        (tmp_path / "posgrados.csv").write_text(
            "clave,nombre\n"
            "PPCDA,Posgrado en Procesos Culturales para el Diseño y el Arte\n"
            "PDB,Posgrado en Diseño Bioclimático\n",
            encoding="utf-8",
        )
        (tmp_path / "ueas_ejemplo.csv").write_text(
            "area_id,clave,nombre,programa_clave,trimestre,tipo,creditos,url\n"
            "1,1440001,UEA Obligatoria,DiPS,3,OBL,9,\n"
            "2,1441001,UEA Optativa Rango,DiPS,VII-XII,OPT,,\n"
            "1,9000010,UEA Posgrado Demo,PDB,1,OBL,9,\n",
            encoding="utf-8",
        )
        call_command("cargar_catalogos_csv", csv_dir=tmp_path)

        assert Posgrado.objects.count() == 2
        assert list(
            Posgrado.objects.order_by("orden").values_list("clave", flat=True)
        ) == ["PPCDA", "PDB"]
        assert UEA.objects.count() == 3
        uea_pos = UEA.objects.get(clave="9000010")
        assert uea_pos.posgrado.clave == "PDB"
        assert uea_pos.licenciatura is None
        uea_lic = UEA.objects.get(clave="1440001")
        assert uea_lic.licenciatura.clave == "DiPS"
        assert uea_lic.posgrado is None

        # Segunda corrida no duplica.
        call_command("cargar_catalogos_csv", csv_dir=tmp_path)
        assert Posgrado.objects.count() == 2
        assert UEA.objects.count() == 3

    def test_omite_posgrados_si_no_existe_csv(self, db, tmp_path):
        """Si posgrados.csv no existe, el comando no falla y simplemente lo omite."""
        from django.core.management import call_command

        self._escribir_csvs(tmp_path)
        call_command("cargar_catalogos_csv", csv_dir=tmp_path)
        assert Posgrado.objects.count() == 0
        assert UEA.objects.count() == 2
