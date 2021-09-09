# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json
logger = logging.getLogger(__name__)
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.db.models import Sum, Count
from core.views.base import CustomView
from core.utils import utils_dates
from core.models import Prestation
from facturation.forms.recalculer_prestations import Formulaire
from consommations.utils.utils_grille_virtuelle import Grille_virtuelle


def Recalculer(request):
    # Récupération des variables
    selections = json.loads(request.POST.get("selections"))
    date_debut = utils_dates.ConvertDateENGtoDate(request.POST.get("date_debut"))
    date_fin = utils_dates.ConvertDateENGtoDate(request.POST.get("date_fin"))
    idactivite = request.POST.get("idactivite")

    # Traitement
    logger.debug("Lancement procédure de recalcul des prestations...")
    for selection in selections:
        logger.debug("Recalcul des prestations pour %s..." % selection["0"])
        grille = Grille_virtuelle(request=request, idfamille=selection["idfamille"], idindividu=selection["idindividu"], idactivite=idactivite, date_min=date_debut, date_max=date_fin)
        grille.Recalculer_tout()
        grille.Enregistrer()
    logger.debug("Fin de la procédure de recalcul des prestations.")

    return JsonResponse({"resultat": True})


class View(CustomView, TemplateView):
    menu_code = "recalculer_prestations"
    template_name = "facturation/recalculer_prestations.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Recalculer des prestations"
        if "form_parametres" not in kwargs:
            context['form_parametres'] = Formulaire(request=self.request)
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if form.is_valid() == False:
            return self.render_to_response(self.get_context_data(form_parametres=form))

        data = self.Get_resultats(parametres=form.cleaned_data)
        context = {
            "form_parametres": form,
            "data": data,
        }
        return self.render_to_response(self.get_context_data(**context))

    def Get_resultats(self, parametres={}):
        date_debut = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[0])
        date_fin = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[1])
        activite = parametres["activite"]

        # Recherche des résultats dans la db
        individus = Prestation.objects.values("individu", "individu__nom", "individu__prenom", "famille", "famille__nom") \
                                        .filter(date__gte=date_debut, date__lte=date_fin, activite=activite) \
                                        .annotate(total_prestations=Sum("montant"), nbre_prestations=Count("pk"))

        # Création des colonnes
        liste_colonnes = ["Individu", "Famille", "Nbre prestations", "Total prestations"]

        # Création des lignes
        liste_lignes = []
        for individu in individus:
            ligne = {
                "0": "%s %s" % (individu["individu__nom"], individu["individu__prenom"] or ""),
                "1": individu["famille__nom"],
                "2": individu["nbre_prestations"],
                "3": float(individu["total_prestations"]),
                "idindividu": individu["individu"],
                "idfamille": individu["famille"],
            }
            liste_lignes.append(ligne)

        # Préparation des résultats
        data = {
            "date_debut": date_debut,
            "date_fin": date_fin,
            "liste_colonnes": liste_colonnes,
            "liste_lignes": json.dumps(liste_lignes),
            "activite": activite
        }
        return data
