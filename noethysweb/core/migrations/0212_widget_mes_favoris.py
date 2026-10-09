# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.db import migrations


def Ajouter_widget_mes_favoris(apps, schema_editor):
    """ Ajoute le widget Mes favoris sous le widget Messages dans la configuration d'accueil de chaque utilisateur """
    from django.core.cache import cache
    Parametre = apps.get_model("core", "Parametre")
    for parametre in Parametre.objects.filter(nom="configuration_accueil"):
        valeur = parametre.parametre or ""
        if "mes_favoris" not in valeur and '"messages"' in valeur:
            parametre.parametre = valeur.replace('"messages"', '"messages","mes_favoris"', 1)
            parametre.save(update_fields=["parametre"])
            if parametre.utilisateur_id:
                cache.delete("options_interface_user%d" % parametre.utilisateur_id)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0211_frequentation_caf'),
    ]

    operations = [
        migrations.RunPython(Ajouter_widget_mes_favoris, migrations.RunPython.noop),
    ]
