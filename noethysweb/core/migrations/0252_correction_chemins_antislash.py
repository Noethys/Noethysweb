# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.db import migrations
from django.db.models import FileField, F, Value
from django.db.models.functions import Replace


def Corriger_chemins(apps, schema_editor):
    """ Remplace les antislashs (chemins importés depuis Windows, ex : individus\\xxx.jpg) par des slashs
        dans tous les champs fichiers. Sous Linux, ces chemins ne correspondaient pas aux fichiers présents sur le disque. """
    for modele in apps.get_models():
        for champ in modele._meta.concrete_fields:
            if isinstance(champ, FileField):
                modele._base_manager.filter(**{"%s__contains" % champ.name: "\\"}).update(
                    **{champ.name: Replace(F(champ.name), Value("\\"), Value("/"))})


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0251_alter_utilisateur_options"),
    ]

    operations = [
        migrations.RunPython(Corriger_chemins, migrations.RunPython.noop),
    ]
