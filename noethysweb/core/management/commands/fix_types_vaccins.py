# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Fix des types de vaccins et maladies"

    def handle(self, *args, **kwargs):
        from individus.utils import utils_vaccinations
        utils_vaccinations.Importation_vaccins()
        self.stdout.write(self.style.SUCCESS("Fix des types de vaccins et maladies OK"))
