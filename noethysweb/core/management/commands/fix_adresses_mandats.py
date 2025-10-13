# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand
from core.models import Mandat


class Command(BaseCommand):
    help = "Correction de la structuration des adresses des mandats"

    def handle(self, *args, **kwargs):
        from core.utils import utils_adresse
        mandats = Mandat.objects.filter(individu__isnull=True)
        for mandat in mandats:
            if mandat.individu_rue and not mandat.individu_numero:
                detail = utils_adresse.Extraire_numero_rue(rue=mandat.individu_rue)
                if detail:
                    mandat.individu_numero = detail[0]
                    mandat.individu_rue = detail[1]
                    mandat.save()

        self.stdout.write(self.style.SUCCESS("Correction de la structuration des adresses des mandats OK"))
