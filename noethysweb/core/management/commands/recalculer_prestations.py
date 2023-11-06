# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Recalculer les prestations du mois en cours. Préciser date_debut et date_fin OU mois au format AAAA-MM. Exemple : recalculer_prestations --mois 2023-11"

    def add_arguments(self, parser):
        parser.add_argument("--date_debut", type=str, nargs="?", help="Date début au format anglais", default=None)
        parser.add_argument("--date_fin", type=str, nargs="?", help="Date fin au format anglais", default=None)
        parser.add_argument("--mois", type=str, nargs="?", help="Mois au format AAAA-MM", default=None)

    def handle(self, *args, **kwargs):
        import datetime, calendar
        from core.utils import utils_dates

        # Recherche de la période à recalculer
        if kwargs["date_debut"]:
            date_debut = utils_dates.ConvertDateENGtoDate(kwargs["date_debut"])
        if kwargs["date_fin"]:
            date_fin = utils_dates.ConvertDateENGtoDate(kwargs["date_fin"])
        if kwargs["mois"]:
            # Recherche les dates extrêmes du mois
            annee, mois = kwargs["mois"].split("-")
            date_debut = datetime.date(int(annee), int(mois), 1)
            date_fin = datetime.date(int(annee), int(mois), calendar.monthrange(int(annee), int(mois))[1])

        # Recalcul des prestations du mois
        from facturation.utils import utils_recalculer_prestations
        utils_recalculer_prestations.Recalculer(request=None, date_debut=date_debut, date_fin=date_fin)

        self.stdout.write(self.style.SUCCESS("Recalculer les prestations du mois en cours OK"))
