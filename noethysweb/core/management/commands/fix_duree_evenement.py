# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand
from core.models import Consommation


class Command(BaseCommand):
    help = "Correction des heures des consommations événementielles"

    def handle(self, *args, **kwargs):
        """ Applique les heures de l'évènement à chaque consommation """
        for conso in Consommation.objects.select_related("evenement").filter(evenement__isnull=False):
            conso.heure_debut = conso.evenement.heure_debut
            conso.heure_fin = conso.evenement.heure_fin
            conso.save()

        self.stdout.write(self.style.SUCCESS("Correction OK"))
