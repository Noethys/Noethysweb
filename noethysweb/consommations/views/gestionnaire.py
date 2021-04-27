# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.models import Inscription, Activite, Ouverture, Consommation, Famille, Classe
from core.views.base import CustomView
from django.views.generic import TemplateView
from core.utils import utils_dates, utils_dictionnaires
from django.http import HttpResponseRedirect
from django.shortcuts import render
import json, datetime
from consommations.forms.grille_selection_date import Formulaire as form_selection_date
from consommations.forms.grille_ajouter_individu import Formulaire as form_ajouter_individu
from consommations.views.grille import Get_periode, Get_generic_data, Save_grille
from django.db.models import Q, Count
from django.core import serializers


class View(CustomView, TemplateView):
    menu_code = "gestionnaire_conso"
    template_name = "consommations/gestionnaire.html"

    def post(self, request, *args, **kwargs):
        # Si requête de MAJ
        if request.POST.get("type_submit") == "MAJ" or request.POST.get("donnees_ajouter_individu"):
            context = self.get_context_data(**kwargs)
            return render(request, self.template_name, context)

        # Si requête de sauvegarde
        Save_grille(request=request, donnees=json.loads(self.request.POST.get("donnees")))
        return HttpResponseRedirect(reverse_lazy("consommations_toc"))

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Gestionnaire des consommations"
        context['form_selection_date'] = form_selection_date
        context['form_ajouter_individu'] = form_ajouter_individu
        context['data'] = self.Get_data_grille()
        return context

    def Get_data_grille(self):
        data = {"mode": "date", "consommations": {}, "prestations": {}, "memos": {}}

        # Sélections par défaut
        if self.request.POST:
            # Si c'est une MAJ de la page
            donnees_post = json.loads(self.request.POST.get("donnees"))
            data["consommations"] = donnees_post["consommations"]
            data["prestations"] = donnees_post["prestations"]
            data["memos"] = donnees_post["memos"]
            data["periode"] = donnees_post["periode"]
            data["selection_activite"] = Activite.objects.get(pk=donnees_post.get("activite")) if donnees_post.get("activite") else None
            data["selection_groupes"] = [int(idgroupe) for idgroupe in donnees_post.get("groupes", [])] if donnees_post.get("groupes") else None
            data["selection_classes"] = [int(idclasse) for idclasse in donnees_post.get("classes", [])] if donnees_post.get("classes") else None
            data["options"] = donnees_post["options"]
            data["dict_suppressions"] = donnees_post["suppressions"]
        else:
            # Si c'est un chargement initial de la page
            date_jour = str(datetime.date.today())
            data["periode"] = {'mode': 'jour', 'selections': {'jour': date_jour}, 'periodes': ['%s;%s' % (date_jour, date_jour)]}
            data["selection_activite"] = None
            data["selection_groupes"] = None
            data["selection_classes"] = None
            data["options"] = {"cocher_auto_activites": True, "afficher_tous_inscrits": False} # todo: charger paramètre depuis la base de données
            data["dict_suppressions"] = {"consommations": [], "prestations": [], "memos": []}

        # Récupération de la période
        data = Get_periode(data)

        # Recherche des activités ouvertes à la date choisie
        liste_idactivites = [d["activite"] for d in Ouverture.objects.values('activite').filter(date=data["date_min"]).annotate(nbre=Count('pk'))]
        data['liste_activites_possibles'] = Activite.objects.filter(idactivite__in=liste_idactivites)

        # Sélection de l'activité à afficher
        if data['liste_activites_possibles'] and (not data["selection_activite"] or data["selection_activite"] not in data['liste_activites_possibles']):
            data['selection_activite'] = data['liste_activites_possibles'][0]

        # Importation des consommations
        conditions = Q(date=data["date_min"])
        if data["selection_activite"] != None: conditions &= Q(activite=data["selection_activite"])
        if data["selection_groupes"] != None: conditions &= Q(groupe__in=data["selection_groupes"])
        liste_conso = Consommation.objects.filter(conditions)
        data["liste_conso_json"] = serializers.serialize('json', liste_conso)

        # Recherche les individus présents
        liste_idinscriptions = list({conso.inscription_id:None for conso in liste_conso}.keys())

        # Ajoute les éventuelles inscriptions des individus ajoutés manuellement
        for key_case, dict_conso in data["consommations"].items():
            for conso in dict_conso:
                if conso["inscription"] not in liste_idinscriptions and conso["date"] == data["date_min"]:
                    liste_idinscriptions.append(conso["inscription"])

        # Ajouter un nouvel individu
        ajouter_individu = self.request.POST.get("donnees_ajouter_individu")
        if ajouter_individu:
            for inscription in Inscription.objects.filter(individu_id=ajouter_individu, activite=data["selection_activite"]):
                if inscription.pk not in liste_idinscriptions and inscription.Is_inscription_in_periode(data["date_min"], data["date_max"]):
                    liste_idinscriptions.append(inscription.pk)

        # Importation des classes pour le gestionnaire des conso
        data["liste_classes"] = Classe.objects.select_related("ecole").filter(date_debut__lte=data["date_min"], date_fin__gte=data["date_min"]).order_by("ecole__nom", "niveaux__ordre")

        # Sélection des classes
        if not data['selection_classes']:
            data['selection_classes'] = [classe.pk for classe in data['liste_classes']]

        # Importation des inscriptions
        if data["options"]["afficher_tous_inscrits"]:
            conditions = Q(activite=data["selection_activite"])
        else:
            conditions = Q(pk__in=liste_idinscriptions)

        if len(data["selection_classes"]) < len(data["liste_classes"]):
            conditions &= Q(individu__scolarite__classe_id__in=data["selection_classes"])

        data["liste_inscriptions"] = Inscription.objects.select_related('individu', 'activite', 'groupe', 'famille', 'categorie_tarif').filter(conditions).order_by("individu__nom", "individu__prenom")

        # Définit le titre de la grille
        data["titre_grille"] = utils_dates.DateComplete(utils_dates.ConvertDateENGtoDate(data["date_min"]))
        data["titre_grille"] += " - " + data["selection_activite"].nom if data["selection_activite"] else ""

        # Incorpore les données génériques
        data.update(Get_generic_data(data))
        return data

