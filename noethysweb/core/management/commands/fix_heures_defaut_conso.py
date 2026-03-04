# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.core.management.base import BaseCommand
from django.db.models import Q
from core.models import Consommation


class Command(BaseCommand):
    help = "Correction des heures par défaut des consommations de type unitaire. Options : date_debut, date_fin, idactivite."

    def add_arguments(self, parser):
        parser.add_argument("--date_debut", nargs="?", type=lambda s: datetime.datetime.strptime(s, "%d/%m/%Y").date(), help="Date au format FR")
        parser.add_argument("--date_fin", nargs="?", type=lambda s: datetime.datetime.strptime(s, "%d/%m/%Y").date(), help="Date au format FR")
        parser.add_argument("--idactivite", nargs="?", type=int, help="ID de l'activité", default=0)

    def handle(self, *args, **kwargs):
        """ Affecte les heures par défaut aux consommations de type Unitaire """
        nbre_corrections = 0
        conditions = (Q(heure_debut__isnull=True) | Q(heure_fin__isnull=True))
        if kwargs["idactivite"]:
            conditions &= Q(activite_id=kwargs["idactivite"])
        if kwargs["date_debut"]:
            conditions &= Q(date__gte=kwargs["date_debut"])
        if kwargs["date_fin"]:
            conditions &= Q(date__lte=kwargs["date_fin"])
        for conso in Consommation.objects.select_related("unite").filter(conditions):
            if conso.unite.type == "Unitaire" and conso.unite.heure_debut and conso.unite.heure_fin:
                if not conso.heure_debut:
                    conso.heure_debut = conso.unite.heure_debut
                if not conso.heure_fin:
                    conso.heure_fin = conso.unite.heure_fin
                conso.save()
                nbre_corrections += 1

        self.stdout.write(self.style.SUCCESS("Correction de %d consommations OK" % nbre_corrections))
