# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Correction automatique des anomalies"

    def handle(self, *args, **kwargs):
        from outils.views import correcteur
        liste_anomalies = []
        for idcategorie, anomalies_temp in correcteur.Get_anomalies().items():
            liste_anomalies += anomalies_temp
        correcteur.Corrige_anomalies(request=None, anomalies=[anomalie.pk for anomalie in liste_anomalies if anomalie.corrigeable])
