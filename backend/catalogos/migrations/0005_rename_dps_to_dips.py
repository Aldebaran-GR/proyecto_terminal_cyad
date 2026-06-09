"""Renombra la clave de la 4ª licenciatura: DPS → DiPS.

El CSV institucional (`licenciaturas.csv`) usa "DiPS" como clave oficial.
Esta migración es idempotente: no falla si la fila no existe o ya está renombrada.
"""

from django.db import migrations


def rename_dps_to_dips(apps, schema_editor):
    Licenciatura = apps.get_model("catalogos", "Licenciatura")
    Licenciatura.objects.filter(clave="DPS").update(clave="DiPS")


def rename_dips_to_dps(apps, schema_editor):
    Licenciatura = apps.get_model("catalogos", "Licenciatura")
    Licenciatura.objects.filter(clave="DiPS").update(clave="DPS")


class Migration(migrations.Migration):

    dependencies = [
        ("catalogos", "0004_area_uea_area_remove_etapa_trimestre_char"),
    ]

    operations = [
        migrations.RunPython(rename_dps_to_dips, rename_dips_to_dps),
    ]
