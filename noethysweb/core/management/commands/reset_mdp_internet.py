# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Reset des mdp internet'

    def handle(self, *args, **kwargs):
        from fiche_famille.utils import utils_internet
        utils_internet.ReinitTousMdp()
        self.stdout.write(self.style.SUCCESS("Reset des mdp internet OK"))
