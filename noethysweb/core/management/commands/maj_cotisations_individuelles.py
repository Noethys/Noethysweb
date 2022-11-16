# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "MAJ des cotisations individuelles sans idfamille"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("MAJ des cotisations individuelles sans idfamille..."))
        from individus.utils import utils_individus
        utils_individus.Maj_cotisations_individuelles()
        self.stdout.write(self.style.SUCCESS("MAJ des cotisations individuelles sans idfamille OK."))
