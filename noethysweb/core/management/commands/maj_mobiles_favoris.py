# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand
from core.models import Famille, Rattachement


class Command(BaseCommand):
    help = 'MAJ des mobiles favoris des familles'

    def handle(self, *args, **kwargs):
        # MAJ des informations des familles
        for famille in Famille.objects.all():
            if not famille.mobile:
                # Recherche un numéro de mobile valide parmi les titulaires de la famille
                for rattachement in Rattachement.objects.prefetch_related('individu').filter(famille=famille, categorie=1, titulaire=True).order_by("pk"):
                    if rattachement.individu.tel_mobile:
                        famille.mobile = rattachement.individu.tel_mobile
                        famille.save()
                        break

        self.stdout.write(self.style.SUCCESS("MAJ des mobiles favoris des familles OK"))
