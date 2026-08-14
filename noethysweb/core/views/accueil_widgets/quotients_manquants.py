# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime
logger = logging.getLogger(__name__)
from django.db.models import Q
from core.views import accueil_widget
from core.models import Tarif, Quotient, Prestation, Famille


class Widget(accueil_widget.Widget):
    code = "quotients_manquants"
    label = "Quotients manquants"

    def init_context_data(self):
        self.context["quotients_manquants"] = self.Get_quotients_manquants()

    def Get_quotients_manquants(self):
        resultats = []

        # Période à étudier
        date_debut, date_fin = (datetime.date.today() - datetime.timedelta(days=40), datetime.date.today())

        # Recherche des familles sans quotient
        tarifs = Tarif.objects.filter((Q(date_fin__isnull=True) | Q(date_fin__gte=date_debut)), date_debut__lte=date_fin, methode__icontains="qf").values_list("pk", flat=True).distinct()
        familles_avec_quotients = Quotient.objects.filter(date_debut__lte=date_fin, date_fin__gte=date_debut).values_list("famille_id", flat=True).distinct()
        familles_avec_prestations = Prestation.objects.filter(tarif__in=tarifs, date__gte=date_debut, date__lte=date_fin).values_list("famille_id", flat=True).distinct()
        familles_sans_quotient = Famille.objects.values_list("pk", "nom").filter(pk__in=familles_avec_prestations).exclude(pk__in=familles_avec_quotients).order_by("nom")

        # Mise en forme des données
        for idfamille, nom_famille in familles_sans_quotient:
            resultats.append({"titre": nom_famille, "idfamille": idfamille})

        return resultats
