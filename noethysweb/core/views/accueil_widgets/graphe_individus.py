# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime, json
logger = logging.getLogger(__name__)
from django.db.models import Count, Q
from core.models import Consommation, Ouverture
from core.views import accueil_widget
from core.utils import utils_parametres


class Widget(accueil_widget.Widget):
    code = "graphe_individus"
    label = "Graphique du nombre d'individus"

    def init_context_data(self):
        self.context['graphique_individus_activite'] = utils_parametres.Get(nom="activite", categorie="graphique_individus", utilisateur=self.request.user if self.request else None, valeur=0)
        self.context['graphique_individus'] = self.Get_graphique_individu(idactivite=self.context['graphique_individus_activite'])

    def Get_graphique_individu(self, idactivite=0):
        conditions = Q(activite_id=idactivite) & Q(date__gte=datetime.date.today() - datetime.timedelta(days=10)) & Q(date__lte=datetime.date.today() + datetime.timedelta(days=30))
        liste_ouvertures = Ouverture.objects.values("date").filter(conditions).distinct().order_by("date")
        consommations = {item["date"]: item["nbre"] for item in Consommation.objects.values("date").filter(conditions, etat__in=("reservation", "present")).annotate(nbre=Count("individu_id"))}
        liste_labels, liste_valeurs = [], []
        for ouverture in liste_ouvertures:
            liste_labels.append(str(ouverture["date"]))
            liste_valeurs.append(consommations.get(ouverture["date"], 0))
        return {"labels": json.dumps(liste_labels), "valeurs": json.dumps(liste_valeurs)}
