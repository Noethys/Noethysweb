# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand
from core.models import Mandat


class Command(BaseCommand):
    help = "Correction des mandats"

    def handle(self, *args, **kwargs):
        # Remplace la séquence 'auto' par 'RCUR'
        for mandat in Mandat.objects.all():
            if mandat.sequence == "auto":
                mandat.sequence = "RCUR"
                mandat.save()

        self.stdout.write(self.style.SUCCESS("Correction des mandats OK"))
