# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand
from django.db.models import Q
from core.models import Historique


class Command(BaseCommand):
    help = "Correction de la date de l'historique"

    def handle(self, *args, **kwargs):
        # Enregistre la date de l'action dans le nouveau champ date de l'historique
        from core.utils import utils_dates
        liste_modifications = []
        for historique in Historique.objects.filter((Q(titre="Ajout d'une consommation") | Q(titre="Suppression d'une consommation"))):
            historique.date = utils_dates.ConvertDateFRtoDate(historique.detail.split(" du ")[1].split(" (")[0])
            liste_modifications.append(historique)
        Historique.objects.bulk_update(liste_modifications, ["date"], batch_size=50)

        self.stdout.write(self.style.SUCCESS("Correction des dates de l'historique OK"))
