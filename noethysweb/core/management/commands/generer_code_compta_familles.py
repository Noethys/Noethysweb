# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand
from core.models import Famille, Rattachement


class Command(BaseCommand):
    help = "Générer le code compta de chaque famille"

    def handle(self, *args, **kwargs):
        from individus.utils.utils_familles import Generer_code_compta_famille
        for famille in Famille.objects.all():
            code_compta = Generer_code_compta_famille(famille=famille)
            if code_compta:
                famille.code_compta = code_compta
                famille.save()

        self.stdout.write(self.style.SUCCESS("Génération code compte familles OK"))
