# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Correction des listes de diffusion"

    def handle(self, *args, **kwargs):
        from core.models import PortailRenseignement
        PortailRenseignement.objects.filter(code="listes_diffusion").delete()
