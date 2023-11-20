# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "MAJ des montants des dépôts"

    def handle(self, *args, **kwargs):
        from reglements.utils import utils_depots
        utils_depots.Maj_montant_depots()
        self.stdout.write(self.style.SUCCESS("MAJ montant dépôts OK"))
