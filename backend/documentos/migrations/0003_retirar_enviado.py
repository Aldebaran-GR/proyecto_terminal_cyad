"""Retira el estado ENVIADO de documentos.

Convierte primero todas las filas en estado='ENVIADO' a 'PUBLICADO' para no
dejar valores fuera de las nuevas choices, y luego restringe el campo.
"""

from django.db import migrations, models


def _convertir_enviado_a_publicado(apps, schema_editor):
    CartaTematica = apps.get_model("documentos", "CartaTematica")
    RequisitoRecuperacion = apps.get_model("documentos", "RequisitoRecuperacion")
    CartaTematica.objects.filter(estado="ENVIADO").update(estado="PUBLICADO")
    RequisitoRecuperacion.objects.filter(estado="ENVIADO").update(estado="PUBLICADO")


def _noop(apps, schema_editor):
    # No hay forma sensata de reconstruir cuáles eran ENVIADO. Quedan en PUBLICADO.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('documentos', '0002_rediseno_documentos'),
    ]

    operations = [
        # 1) Convertir datos existentes antes de cambiar choices
        migrations.RunPython(_convertir_enviado_a_publicado, _noop),
        # 2) Restringir choices al nuevo conjunto {BORRADOR, PUBLICADO}
        migrations.AlterField(
            model_name='cartatematica',
            name='estado',
            field=models.CharField(
                choices=[('BORRADOR', 'Borrador'), ('PUBLICADO', 'Publicado')],
                default='BORRADOR', max_length=10, verbose_name='Estado',
            ),
        ),
        migrations.AlterField(
            model_name='requisitorecuperacion',
            name='estado',
            field=models.CharField(
                choices=[('BORRADOR', 'Borrador'), ('PUBLICADO', 'Publicado')],
                default='BORRADOR', max_length=10, verbose_name='Estado',
            ),
        ),
    ]
