# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0205_alter_utilisateur_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='activite',
            name='portail_masquer_capacite',
            field=models.BooleanField(default=False, verbose_name="Masquer la capacité d'accueil dans le planning"),
        ),
    ]
