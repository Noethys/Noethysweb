# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand
from core.models import Consommation


class Command(BaseCommand):
    help = "Correction des heures par défaut des consommations de type unitaire "

    def handle(self, *args, **kwargs):
        """ Affecte les heures par défaut aux consommations de type Unitaire """
        nbre_corrections = 0
        for conso in Consommation.objects.select_related("unite").filter(heure_debut__isnull=True, heure_fin__isnull=True):
            if conso.unite.type == "Unitaire" and conso.unite.heure_debut and conso.unite.heure_fin:
                conso.heure_debut = conso.unite.heure_debut
                conso.heure_fin = conso.unite.heure_fin
                conso.save()
                nbre_corrections += 1

        self.stdout.write(self.style.SUCCESS("Correction de %d consommations OK" % nbre_corrections))
