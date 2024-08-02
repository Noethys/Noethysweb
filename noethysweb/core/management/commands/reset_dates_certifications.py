# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand
from core.models import Famille, Rattachement


class Command(BaseCommand):
    help = "Reset des dates de certification des fiches familles et individuelles"

    def handle(self, *args, **kwargs):
        Famille.objects.all().update(certification_date=None)
        Rattachement.objects.all().update(certification_date=None)
        self.stdout.write(self.style.SUCCESS("Reset dates certifications OK"))
