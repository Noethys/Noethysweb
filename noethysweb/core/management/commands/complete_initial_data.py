# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand
from django.core import serializers


class Command(BaseCommand):
    help = "Importe compléments pour initial data"

    def handle(self, *args, **kwargs):

        # Importation des modèles d'emails
        fixture = open("core/static/defaut/modeles_emails.json", "rb")
        for objet_json in serializers.deserialize("json", fixture, ignorenonexistent=True):
            # Ajoute le modèle uniquement s'il n'existe aucun modèle pour cette catégorie
            if objet_json.object._meta.model.objects.filter(categorie=objet_json.object.categorie).count() == 0:
                self.stdout.write("Ajout du modèle d'emails %s" % objet_json.object.categorie)
                objet_json.object.pk = None
                objet_json.save()
        fixture.close()

        # Modification des types de vaccins et types de maladies
        from individus.utils import utils_vaccinations
        utils_vaccinations.Importation_vaccins()

        self.stdout.write(self.style.SUCCESS("Compléments installés"))
