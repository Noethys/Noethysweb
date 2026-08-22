# -*- coding: utf-8 -*-

import datetime

from consommations.views import pointeuse


class View(pointeuse.View):
    """Interface simplifiée d'émargement.

    Le gestionnaire standard reste responsable de toute la construction de la
    grille et de la logique métier. On lui demande simplement d'inclure tous
    les inscrits actifs de l'activité, même lorsqu'aucune consommation n'existe
    encore pour eux.
    """

    menu_code = "pointeuse_conso"
    template_name = "consommations/emargement.html"
    afficher_inscrits_sans_conso = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_titre"] = "Émargement"

        date_courante = context["data"]["date_min"]
        if isinstance(date_courante, str):
            date_courante = datetime.datetime.strptime(date_courante, "%Y-%m-%d").date()

        context["emargement_date"] = date_courante
        context["emargement_date_iso"] = date_courante.isoformat()
        context["emargement_date_precedente"] = (date_courante - datetime.timedelta(days=1)).isoformat()
        context["emargement_date_suivante"] = (date_courante + datetime.timedelta(days=1)).isoformat()
        context["emargement_activite"] = context["data"].get("selection_activite")
        return context
