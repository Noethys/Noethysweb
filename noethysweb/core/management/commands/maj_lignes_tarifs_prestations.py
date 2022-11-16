# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "MAJ des lignes de tarifs dans les prestations"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("MAJ des lignes de tarifs dans les prestations..."))
        from individus.utils import utils_individus
        utils_individus.Maj_lignes_tarifs_prestations()
        self.stdout.write(self.style.SUCCESS("MAJ des lignes de tarifs dans les prestations OK."))
