# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'MAJ des soldes des factures'

    def handle(self, *args, **kwargs):
        # MAJ des totaux et des soldes des factures
        from facturation.utils import utils_factures
        utils_factures.Maj_total_factures(IDfamille=0, IDfacture=0)
        utils_factures.Maj_solde_actuel_factures()
        self.stdout.write(self.style.SUCCESS("MAJ des totaux et des soldes des factures OK"))
