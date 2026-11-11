# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.db import migrations


def Initialiser_modeles_pes(apps, schema_editor):
    """ Les champs edition_asap et inclure_pieces_jointes n'étaient pas utilisés par le format PES ORMC.
    Leurs valeurs par défaut (01 et True) sont neutralisées pour conserver le comportement actuel des exports. """
    PesModele = apps.get_model("core", "PesModele")
    PesModele.objects.filter(format="pes").update(edition_asap="", inclure_pieces_jointes=False, type_pj="007")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0222_alter_pesmodele_format"),
    ]

    operations = [
        migrations.RunPython(Initialiser_modeles_pes, migrations.RunPython.noop),
    ]
