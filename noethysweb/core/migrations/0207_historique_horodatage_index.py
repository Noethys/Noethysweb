# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0206_activite_portail_masquer_capacite"),
    ]

    operations = [
        migrations.AlterField(
            model_name="historique",
            name="horodatage",
            field=models.DateTimeField(verbose_name="Horodatage", auto_now_add=True, db_index=True),
        ),
    ]
