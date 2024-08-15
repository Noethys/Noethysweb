# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.conf import settings
from core.models import Historique


class Command(BaseCommand):
    """ Purge auto de l'historique pour cron """
    help = "Purge automatique de l'historique"

    def handle(self, *args, **kwargs):
        if settings.PURGE_HISTORIQUE_JOURS:
            conditions = Q(horodatage__date__lte=datetime.datetime.now() - datetime.timedelta(days=settings.PURGE_HISTORIQUE_JOURS))
            resultat = Historique.objects.filter(conditions).delete()
            self.stdout.write(self.style.SUCCESS("Purge auto de l'historique OK : %d suppressions." % resultat[0]))
