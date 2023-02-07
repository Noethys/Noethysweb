# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime
logger = logging.getLogger(__name__)
from core.views import accueil_widget
from core.models import Activite
from cotisations.utils import utils_cotisations_manquantes


class Widget(accueil_widget.Widget):
    code = "cotisations_manquantes"
    label = "Adhésions manquantes"

    def init_context_data(self):
        self.context["cotisations_manquantes"] = self.Get_cotisations_manquantes()

    def Get_cotisations_manquantes(self):
        resultats = []

        # Recherche des cotisations manquantes
        date_reference = datetime.date.today()
        liste_activites = Activite.objects.all()
        presents = (date_reference - datetime.timedelta(days=30), date_reference + datetime.timedelta(days=30))
        dictPieces = utils_cotisations_manquantes.Get_liste_cotisations_manquantes(date_reference=date_reference, activites=liste_activites,
                                                                                   presents=presents, only_concernes=True)
        # Mise en forme des données
        for idfamille, valeurs in dictPieces.items():
            resultats.append({"titre": valeurs["nom_famille"], "detail": valeurs["texte"], "idfamille": idfamille})

        return resultats
