# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, datetime
from django.urls import reverse_lazy
from django.db.models import Q, Count
from django.core import serializers
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib import messages
from core.models import Inscription, Activite, Ouverture, Consommation, Famille, Classe, NiveauScolaire
from core.views.base import CustomView
from core.utils import utils_dates, utils_dictionnaires, utils_parametres
from consommations.forms.grille_selection_date import Formulaire as form_selection_date
from consommations.forms.grille_ajouter_individu import Formulaire as form_ajouter_individu
from consommations.forms.grille_options import Formulaire as form_options
from consommations.forms.grille_forfaits import Formulaire as form_forfaits
from consommations.views.grille import Get_periode, Get_generic_data, Save_grille


class View(CustomView, TemplateView):
    menu_code = "gestionnaire_conso"
    template_name = "consommations/gestionnaire.html"
    mode_grille = "date"

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
        if context['data']["tarifs_credits_exists"]:
            context['form_forfaits'] = form_forfaits(inscriptions=context['data']["liste_inscriptions"])
        context['form_options'] = form_options(initial=context["data"]["options"])
        return context

    def Get_data_grille(self):
        data = {"mode": self.mode_grille, "consommations": {}, "prestations": {}, "memos": {}}
        options_defaut = {"tri": "nom", "afficher_date_naiss": "non", "afficher_age": "non", "afficher_groupe": "non", "afficher_classe": "non", "afficher_niveau_scolaire": "non", "afficher_presents_totaux": "non"}

        # Sélections par défaut
        if self.request.POST:
            # Si c'est une MAJ de la page
            donnees_post = json.loads(self.request.POST.get("donnees"))
            data["consommations"] = donnees_post["consommations"]
            data["prestations"] = donnees_post["prestations"]
            data["memos"] = donnees_post["memos"]
            data["periode"] = donnees_post["periode"]
            data["selection_activite"] = Activite.objects.get(pk=donnees_post.get("activite")) if donnees_post.get("activite") else None
            data["ancienne_activite"] = donnees_post.get("ancienne_activite", None)
            data["selection_groupes"] = [int(idgroupe) for idgroupe in donnees_post.get("groupes", [])] if donnees_post.get("groupes") else None
            data["selection_classes"] = [int(idclasse) for idclasse in donnees_post.get("classes", [])] if donnees_post.get("classes") else None
            data["options"] = donnees_post["options"]
            data["dict_suppressions"] = donnees_post["suppressions"]
            data["mode_parametres"] = donnees_post.get("mode_parametres", None)

            # Enregistrement des options
            if isinstance(data["options"], list):
                data["options"] = {item["name"]: item["value"] for item in data["options"] if item["name"] != "csrfmiddlewaretoken"}
            utils_parametres.Set_categorie(categorie="gestionnaire_%s" % self.mode_grille, utilisateur=self.request.user, parametres=data["options"])

        else:
            # Si c'est un chargement initial de la page
            date_jour = str(datetime.date.today())
            data["periode"] = {'mode': 'jour', 'selections': {'jour': date_jour}, 'periodes': ['%s;%s' % (date_jour, date_jour)]}
            data["selection_activite"] = None
            data["selection_groupes"] = None
            data["selection_classes"] = None
            data["options"] = utils_parametres.Get_categorie(categorie="gestionnaire_%s" % self.mode_grille, utilisateur=self.request.user, parametres=options_defaut)
            data["options"].update(utils_parametres.Get_categorie(categorie="grille", utilisateur=self.request.user, parametres={"afficher_quantites": False}))
            data["dict_suppressions"] = {"consommations": [], "prestations": [], "memos": []}

        # Récupération de la période
        data = Get_periode(data)

        # Recherche des activités ouvertes à la date choisie
        liste_idactivites = [d["activite"] for d in Ouverture.objects.values('activite').filter(date=data["date_min"]).annotate(nbre=Count('pk'))]
        data['liste_activites_possibles'] = Activite.objects.filter(idactivite__in=liste_idactivites, structure__in=self.request.user.structures.all())

        # Sélection de l'activité à afficher
        if data['liste_activites_possibles'] and (not data["selection_activite"] or data["selection_activite"] not in data['liste_activites_possibles']):
            data['selection_activite'] = data['liste_activites_possibles'][0]

        # Si changement d'activité, on réinitialise la sélection des groupes
        if data.get("ancienne_activite", None) != (data["selection_activite"].pk if data["selection_activite"] else None):
            data["selection_groupes"] = None

        # Importation des consommations
        conditions = Q(date=data["date_min"])
        if data["selection_activite"] != None: conditions &= Q(activite=data["selection_activite"])
        if data["selection_groupes"] != None: conditions &= Q(groupe__in=data["selection_groupes"])
        data["liste_conso"] = Consommation.objects.filter(conditions)
        data["liste_conso_json"] = serializers.serialize('json', data["liste_conso"])

        # Recherche les individus présents
        liste_idinscriptions = list({conso.inscription_id:None for conso in data["liste_conso"]}.keys())

        # Ajoute les éventuelles inscriptions des individus ajoutés manuellement
        selection_idactivite = data["selection_activite"].pk if data["selection_activite"] else None
        for key_case, dict_conso in data["consommations"].items():
            for conso in dict_conso:
                if conso["inscription"] not in liste_idinscriptions and str(conso["date"]) == str(data["date_min"]) and conso["activite"] == selection_idactivite and (not data["selection_groupes"] or conso["groupe"] in data["selection_groupes"]):
                    liste_idinscriptions.append(conso["inscription"])

        # Ajouter un nouvel individu
        ajouter_individu = self.request.POST.get("donnees_ajouter_individu")
        if ajouter_individu and not ajouter_individu.startswith("INSCRITS"):
            selection_ajouter_individu = [int(idindividu) for idindividu in ajouter_individu.split(";")]
            for inscription in Inscription.objects.select_related("individu").filter(individu_id__in=selection_ajouter_individu, activite=data["selection_activite"]):
                if inscription.pk not in liste_idinscriptions:
                    if inscription.Is_inscription_in_periode(data["date_min"], data["date_max"]):
                        liste_idinscriptions.append(inscription.pk)
                    else:
                        messages.add_message(self.request, messages.INFO, "L'inscription de %s n'est pas active sur cette date" % inscription.individu.Get_nom())

        # Importation des classes
        liste_classes = Classe.objects.select_related("ecole").filter(date_debut__lte=data["date_min"], date_fin__gte=data["date_min"]).order_by("ecole__nom", "niveaux__ordre", "nom")
        data["liste_classes"] = list({classe: True for classe in liste_classes}.keys())
        data["liste_ecoles"] = list({classe.ecole: True for classe in liste_classes}.keys())

        # # Tri des classes par niveau scolaire
        # dict_niveaux = {niveau.pk: niveau for niveau in NiveauScolaire.objects.all()}
        # dict_classes = {classe.pk: classe for classe in liste_classes}
        # dict_niveaux_classes = {}
        # for classe_niveaux in Classe.niveaux.through.objects.filter(classe__in=liste_classes):
        #     dict_niveaux_classes.setdefault(classe_niveaux.classe_id, [])
        #     dict_niveaux_classes[classe_niveaux.classe_id].append(dict_niveaux[classe_niveaux.niveauscolaire_id].ordre)
        # liste_temp = sorted([(sorted(niveaux), idclasse) for idclasse, niveaux in dict_niveaux_classes.items()])
        # data["liste_classes"] = [dict_classes[idclasse] for niveaux, idclasse in liste_temp]

        # Sélection des classes
        if not data['selection_classes']:
            data['selection_classes'] = [classe.pk for classe in data['liste_classes']]

        # Importation des inscriptions
        conditions = Q(date_debut__lte=data["date_min"]) & (Q(date_fin__isnull=True) | Q(date_fin__gte=data["date_max"]))
        if ajouter_individu == "INSCRITS_TOUS":
            conditions &= Q(activite=data["selection_activite"])
        elif ajouter_individu and ajouter_individu.startswith("INSCRITS_GROUPE"):
            conditions &= Q(activite=data["selection_activite"], groupe_id=int(ajouter_individu.split(":")[1])) | Q(pk__in=liste_idinscriptions)
        else:
            conditions &= Q(pk__in=liste_idinscriptions)

        if len(data["selection_classes"]) < len(data["liste_classes"]):
            conditions &= Q(individu__scolarite__classe_id__in=data["selection_classes"])

        if data["options"].get("tri", "nom") == "prenom":
            tri = ("individu__prenom", "individu__nom")
        else:
            tri = ("individu__nom", "individu__prenom")
        data["liste_inscriptions"] = Inscription.objects.select_related('individu', 'activite', 'groupe', 'famille', 'categorie_tarif').filter(conditions).order_by(*tri)

        if data["options"].get("tri") == "date_naiss":
            data["liste_inscriptions"] = sorted(data["liste_inscriptions"], key=lambda x: x.individu.date_naiss or datetime.date(1900, 1, 1), reverse=True)

        # Définit le titre de la grille
        data["titre_grille"] = utils_dates.DateComplete(utils_dates.ConvertDateENGtoDate(data["date_min"]))
        data["titre_grille"] += " - " + data["selection_activite"].nom if data["selection_activite"] else ""

        # Incorpore les données génériques
        data.update(Get_generic_data(data))
        return data

