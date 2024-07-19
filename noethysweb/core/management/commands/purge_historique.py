# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.core.management.base import BaseCommand
from django.db.models import Q
from core.models import Historique


class Command(BaseCommand):
    """ Utilisation : purge_historique --idfamille 0 --date 18/07/2024 """
    help = "Purge de l'historique"

    def add_arguments(self, parser):
        parser.add_argument("--idfamille", type=int, help="ID de la famille ou 0 pour toutes les familles")
        parser.add_argument("--date", type=lambda s: datetime.datetime.strptime(s, "%d/%m/%Y").date())

    def handle(self, *args, **kwargs):
        conditions = Q(horodatage__date__lte=kwargs["date"])
        if kwargs["idfamille"]:
            conditions &= Q(famille_id=kwargs["idfamille"])
        Historique.objects.filter(conditions).delete()
        self.stdout.write(self.style.SUCCESS("Purge de l'historique OK"))
