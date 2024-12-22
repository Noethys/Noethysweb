# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.shortcuts import render
from core.utils import utils_parametres
from core.models import Inscription, Activite, JOURS_COMPLETS_SEMAINE
from core.views.base import CustomView
from consommations.views.grille import Get_periode, Get_generic_data, Save_grille
from consommations.forms.grille_traitement_lot import Formulaire as form_traitement_lot
from consommations.forms.appliquer_semaine_type import Formulaire as form_appliquer_semaine_type
from consommations.forms.grille_forfaits import Formulaire as form_forfaits


class Onglet(CustomView):
    menu_code = "individus_toc"

    def get_context_data(self, **kwargs):
        context = super(Onglet, self).get_context_data(**kwargs)
        context['page_titre'] = "Grille des consommations"
        return context



class Modifier(Onglet, TemplateView):
    template_name = "fiche_famille/famille_grille.html"

    def post(self, request, *args, **kwargs):
        # Si requête de MAJ
        if request.POST.get("type_submit") == "MAJ":
            context = self.get_context_data(**kwargs)
            return render(request, self.template_name, context)

        # Si requête de sauvegarde
        Save_grille(request=request, donnees=json.loads(self.request.POST.get("donnees")))
        return HttpResponseRedirect(reverse_lazy("famille_resume", args=(self.kwargs['idfamille'],)))

    def get_context_data(self, **kwargs):
        context = super(Modifier, self).get_context_data(**kwargs)
        self.IDfamille = self.kwargs.get('idfamille', None)
        self.IDindividu = self.kwargs.get('idindividu', None)
        context['idfamille'] = self.IDfamille
        context['idindividu'] = self.IDindividu
        context['form_traitement_lot'] = form_traitement_lot
        context['form_appliquer_semaine_type'] = form_appliquer_semaine_type
        context['jours_complets_semaine'] = JOURS_COMPLETS_SEMAINE
        context['data'] = self.Get_data_grille()
        if context['data']["tarifs_credits_exists"]:
            context['form_forfaits'] = form_forfaits(inscriptions=context['data']["liste_inscriptions"])
        return context

    def Get_data_grille(self):
        data = {"mode": "individu", "idfamille": self.IDfamille, "consommations": {}, "prestations": {}, "memos": {}}

        # Sélections par défaut
        if self.request.POST:
            # Si c'est une MAJ de la page
            donnees_post = json.loads(self.request.POST.get("donnees"))
            data["consommations"] = donnees_post["consommations"]
            data["prestations"] = donnees_post["prestations"]
            data["memos"] = donnees_post["memos"]
            data["periode"] = donnees_post["periode"]
            data["options"] = donnees_post["options"]
            data["dict_suppressions"] = donnees_post["suppressions"]
            data["selection_individus"] = [int(idindividu) for idindividu in donnees_post["individus"]] if donnees_post["individus"] else "__all__"
            data["selection_activite"] = Activite.objects.get(pk=donnees_post.get("activite")) if donnees_post.get("activite") else None
        else:
            # Si c'est un chargement initial de la page
            data["periode"] = utils_parametres.Get(nom="periode", categorie="suivi_consommations", utilisateur=self.request.user, valeur={})
            data["options"] = utils_parametres.Get_categorie(categorie="grille", utilisateur=self.request.user, parametres={"afficher_quantites": False})
            data["selection_individus"] = [self.IDindividu,] if self.IDindividu != None else "__all__"
            data["selection_activite"] = None
            data["dict_suppressions"] = {"consommations": [], "prestations": [], "memos": []}

        # Récupération de la période
        data = Get_periode(data)
        # logger.debug("Période de la grille =", data)

        # Importation de toutes les inscriptions de la famille sur la période sélectionnée
        dict_inscriptions = {}
        data["liste_individus_possibles"] = []
        data['liste_activites_possibles'] = []
        for inscription in Inscription.objects.select_related('individu', 'activite', 'groupe', 'famille', 'categorie_tarif').filter(famille__pk=self.IDfamille, activite__structure__in=self.request.user.structures.all()).order_by("individu__prenom"):
            if inscription.Is_inscription_in_periode(data["date_min"], data["date_max"]):
                # Conserve les inscriptions disponibles
                if data["selection_individus"] == "__all__" or inscription.individu_id in data["selection_individus"]:
                    dict_inscriptions.setdefault(inscription.activite, [])
                    dict_inscriptions[inscription.activite].append(inscription)
                # Conserve les activités possibles
                if inscription.activite not in data['liste_activites_possibles']:
                    data['liste_activites_possibles'].append(inscription.activite)
                # Conserve les individus possibles
                if inscription.individu not in data["liste_individus_possibles"]:
                    data["liste_individus_possibles"].append(inscription.individu)

        # Mémorise l'activité favorite
        key_cache = "activite_favorite_user%d" % self.request.user.pk
        if data["selection_activite"]:
            cache.set(key_cache, data["selection_activite"])
        activite_favorite = cache.get(key_cache, None)
        if not data["selection_activite"] and activite_favorite in data['liste_activites_possibles']:
            data['selection_activite'] = activite_favorite

        # Sélection de l'activité à afficher
        if data['liste_activites_possibles'] and not data["selection_activite"]:
            data['selection_activite'] = data['liste_activites_possibles'][0]
        data["liste_inscriptions"] = dict_inscriptions.get(data['selection_activite'], [])

        # Définit le titre de la grille
        data["titre_grille"] = "Aucun activité sélectionnée"
        if data["selection_activite"]:
            data["titre_grille"] = data["selection_activite"].nom

        # Incorpore les données génériques
        data.update(Get_generic_data(data))

        # Liste des dates modifiables pour l'application d'une semaine-type
        if data["liste_dates"]:
            data["date_modifiable_min"] = min(data["liste_dates"])
            data["date_modifiable_max"] = max(data["liste_dates"])
        data["jours_semaine_modifiables"] = [0, 1, 2, 3, 4, 5, 6]

        return data

