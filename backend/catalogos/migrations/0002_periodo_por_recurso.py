"""Periodo activo por recurso: agrega 3 flags y preserva el flag legado `activo`
copiándolo a los tres nuevos para los periodos existentes que ya estuvieran activos.
"""

from django.db import migrations, models


def copy_activo_to_per_resource(apps, schema_editor):
    """Para cada Periodo con activo=True, marca los tres flags por recurso en True
    para preservar la semántica previa ("activo para todo")."""
    Periodo = apps.get_model("catalogos", "Periodo")
    for p in Periodo.objects.filter(activo=True):
        Periodo.objects.filter(pk=p.pk).update(
            activo_cartas=True,
            activo_requisitos=True,
            activo_autoevaluacion=True,
        )


def reverse_copy(apps, schema_editor):
    """Reverso: si cualquiera de los flags por recurso está en True, `activo` queda True.
    (Es el mismo cálculo que hace save() del modelo, pero aquí lo hacemos a mano
    para que la migración inversa deje datos coherentes.)"""
    Periodo = apps.get_model("catalogos", "Periodo")
    for p in Periodo.objects.all():
        nuevo_activo = bool(
            p.activo_cartas or p.activo_requisitos or p.activo_autoevaluacion
        )
        if p.activo != nuevo_activo:
            Periodo.objects.filter(pk=p.pk).update(activo=nuevo_activo)


class Migration(migrations.Migration):

    dependencies = [
        ("catalogos", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="periodo",
            name="activo_cartas",
            field=models.BooleanField(
                default=False, verbose_name="Activo para Cartas Temáticas"
            ),
        ),
        migrations.AddField(
            model_name="periodo",
            name="activo_requisitos",
            field=models.BooleanField(
                default=False, verbose_name="Activo para Requisitos de Recuperación"
            ),
        ),
        migrations.AddField(
            model_name="periodo",
            name="activo_autoevaluacion",
            field=models.BooleanField(
                default=False, verbose_name="Activo para Autoevaluación"
            ),
        ),
        # `activo` pasa a ser un flag legado, NO editable (se recalcula en save()).
        migrations.AlterField(
            model_name="periodo",
            name="activo",
            field=models.BooleanField(
                default=False,
                editable=False,
                verbose_name="Activo (cualquier recurso)",
            ),
        ),
        migrations.RunPython(copy_activo_to_per_resource, reverse_copy),
    ]
