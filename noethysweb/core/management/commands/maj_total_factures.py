# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'MAJ des totaux des factures'

    def add_arguments(self, parser):
        parser.add_argument("idfamille", type=int, help='ID de la famille ou 0 pour toutes les familles')
        parser.add_argument("idfacture", type=int, help='ID de la facture ou 0 pour toutes les factures')

    def handle(self, *args, **kwargs):
        # MAJ des totaux et soldes des factures
        from facturation.utils import utils_factures
        utils_factures.Maj_total_factures(IDfamille=kwargs["idfamille"], IDfacture=kwargs["idfacture"])
        self.stdout.write(self.style.SUCCESS("MAJ des totaux des factures OK"))
