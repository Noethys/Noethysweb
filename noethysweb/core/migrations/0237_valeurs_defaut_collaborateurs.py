# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.db import migrations


def Remplir(apps, schema_editor):
    """ Remplit avec les valeurs par défaut les listes de paramétrage des collaborateurs encore vides """
    from core.utils.utils_valeurs_defaut_collaborateurs import Remplir_tables_vides
    Remplir_tables_vides(apps)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0236_types_contrats_collaborateurs"),
    ]

    operations = [
        migrations.RunPython(Remplir, migrations.RunPython.noop),
    ]
