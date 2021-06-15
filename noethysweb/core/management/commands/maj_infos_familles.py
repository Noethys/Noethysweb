# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'MAJ des informations'

    def handle(self, *args, **kwargs):
        # MAJ des informations des familles
        from core.utils import utils_db
        utils_db.Maj_infos()
        self.stdout.write(self.style.SUCCESS("MAJ des infos des familles OK"))
