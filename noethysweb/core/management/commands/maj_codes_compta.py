# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand
from core.models import Famille


class Command(BaseCommand):
    help = 'MAJ des codes comptables des familles'

    def handle(self, *args, **kwargs):
        for famille in Famille.objects.all():
            famille.Maj_infos(maj_adresse=False, maj_mail=False, maj_mobile=False, maj_titulaire_helios=False, maj_tiers_solidaire=False, maj_code_compta=True)
        self.stdout.write(self.style.SUCCESS("MAJ des codes comptables des familles OK"))
