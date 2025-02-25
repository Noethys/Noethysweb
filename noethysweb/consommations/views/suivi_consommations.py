# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, json
from django.db.models import Q, Count
from django.shortcuts import render
from django.views.generic import TemplateView
from core.models import Activite, Ouverture, Remplissage, UniteRemplissage, Vacance, Consommation, Evenement, Groupe
from core.views.base import CustomView
from core.utils import utils_dates, utils_parametres


def Get_activites(request=None):
    """ Renvoie une liste d'activités """
    activites = Activite.objects.filter(structure__in=request.user.structures.all()).order_by("-date_fin", "nom")
    context = {"activites": activites}
    return render(request, "consommations/suivi_consommations_activites.html", context)


def Get_parametres(request=None):
    """ Renvoie les paramètres d'affichage """
    parametres = utils_parametres.Get_categorie(categorie="suivi_consommations", utilisateur=request.user, parametres={
        "mode": "places_prises",
        "periode": {},
        "activites": [],
        "afficher_totaux": True,
        "masquer_groupes_fermes": False,
        "afficher_abreges_groupes": False,
        "afficher_abreges_unites": True,
    })
    parametres["periode_json"] = json.dumps(parametres["periode"])
    parametres["activites_json"] = json.dumps(parametres["activites"])
    return parametres


def Get_suivi_consommations(request):
    """ Renvoie le contenu de la table """
    parametres = json.loads(request.POST.get("parametres", None))

    # Si demande de modification des paramètres
    if parametres:
        utils_parametres.Set_categorie(categorie="suivi_consommations", utilisateur=request.user, parametres=parametres)

    # Importation des paramètres
    parametres = Get_parametres(request=request)
    context = {"data_suivi_consommations": Get_data(parametres=parametres, request=request)}
    context.update(parametres)
    return render(request, "consommations/suivi_consommations_tableau.html", context)


class Total():
    def __init__(self):
        self.pk = 999999
        self.nom = "Total"


def Get_data(parametres={}, request=None):
    """ Création des valeurs pour le suivi des consommations """
    # Récupération des paramètres
    mode = parametres.get("mode", "places_prises")
    afficher_totaux = parametres.get("afficher_totaux", True)
    periode = parametres.get("periode", {})
    activites = parametres.get("activites", [])
    masquer_groupes_fermes = parametres.get("masquer_groupes_fermes", False)

    # Apporté par la view liste d'attente
    liste_activites_temp = parametres.get("liste_activites", [])
    conditions_periodes = parametres.get("condition_periodes", [])
    date_min = parametres.get("date_min", None)
    date_max = parametres.get("date_max", None)

    # Importation des activités
    if not liste_activites_temp:
        liste_activites_temp = Activite.objects.select_related("structure").filter(idactivite__in=activites)

    # Vérifie que l'activité est bien accessible pour cet utilisateur
    if request:
        liste_activites = [activite for activite in liste_activites_temp if activite.structure in request.user.structures.all()]
    else:
        liste_activites = liste_activites_temp

    # Récupération de la période
    if not conditions_periodes:
        listes_dates = []
        if periode:
            conditions_periodes = Q()
            for p in periode["periodes"]:
                date_debut = utils_dates.ConvertDateENGtoDate(p.split(";")[0])
                date_fin = utils_dates.ConvertDateENGtoDate(p.split(";")[1])
                listes_dates.extend([date_debut, date_fin])
                conditions_periodes |= Q(date__gte=date_debut) & Q(date__lte=date_fin)
        else:
            d = datetime.date(3000, 1, 1)
            conditions_periodes = Q(date__gte=d) & Q(date__lte=d)
            listes_dates.extend([d, d])

        # Récupération des dates extrêmes
        if listes_dates:
            date_min, date_max = min(listes_dates), max(listes_dates)

    # Importation des unités de remplissage
    liste_unites_remplissage = UniteRemplissage.objects.prefetch_related('activite', 'unites').filter(activite__in=liste_activites, afficher_page_accueil=True).order_by("ordre")
    dict_unites_remplissage = {}
    dict_unites_remplissage_unites = {}
    for unite_remplissage in liste_unites_remplissage:
        dict_unites_remplissage.setdefault(unite_remplissage.activite, [])
        dict_unites_remplissage[unite_remplissage.activite].append(unite_remplissage)
        for unite_conso in unite_remplissage.unites.all():
            dict_unites_remplissage_unites.setdefault(unite_conso.pk, [])
            dict_unites_remplissage_unites[unite_conso.pk].append(unite_remplissage.pk)

    # Importation des ouvertures
    liste_ouvertures = []
    liste_dates = []
    unites_ouvertes = []
    groupes_ouverts = []
    for ouverture in Ouverture.objects.filter(conditions_periodes & Q(activite__in=liste_activites)):
        for id_unite_remplissage in dict_unites_remplissage_unites.get(ouverture.unite_id, []):
            liste_ouvertures.append("%s_%s_%s" % (ouverture.date, id_unite_remplissage, ouverture.groupe_id))
            if ouverture.date not in liste_dates: liste_dates.append(ouverture.date)
            if id_unite_remplissage not in unites_ouvertes: unites_ouvertes.append(id_unite_remplissage)
            if ouverture.groupe_id not in groupes_ouverts: groupes_ouverts.append(ouverture.groupe_id)

    # Récupération des dates
    liste_dates.sort()

    # Importation des vacances
    if date_min and date_max:
        liste_vacances = Vacance.objects.filter(date_fin__gte=date_min, date_debut__lte=date_max)
    else:
        liste_vacances = []

    # Importation des remplissages
    liste_remplissage = Remplissage.objects.filter(conditions_periodes & Q(activite__in=liste_activites))
    dict_capacite = {'%s_%d_%d' % (r.date, r.unite_remplissage_id, r.groupe_id or 0): r.places for r in liste_remplissage}

    # Importation des groupes
    liste_groupes = Groupe.objects.select_related('activite').filter(activite__in=liste_activites).order_by("ordre")
    dict_groupes = {}
    for groupe in liste_groupes:
        dict_groupes.setdefault(groupe.activite, [])
        dict_groupes[groupe.activite].append(groupe)

    # Rajoute un groupe Total
    if afficher_totaux:
        for activite in liste_activites:
            if activite in dict_groupes:
                dict_groupes[activite].append(Total())

    # Importation des places prises
    liste_places = Consommation.objects.values('date', 'unite', 'groupe', 'quantite', 'evenement').annotate(nbre=Count('pk')).filter(conditions_periodes & Q(activite__in=liste_activites) & Q(etat__in=("reservation", "present")))
    dict_places = {}
    for p in liste_places:
        for idgroupe in [p["groupe"], 0]:
            for id_unite_remplissage in dict_unites_remplissage_unites.get(p["unite"], []):
                key = "%s_%d_%d" % (p["date"], id_unite_remplissage or 0, idgroupe or 0)
                quantite = p["nbre"] * p["quantite"] if p["quantite"] else p["nbre"]
                dict_places[key] = dict_places.get(key, 0) + quantite
                if p["evenement"]:
                    key += "_%d" % p["evenement"]
                    dict_places[key] = dict_places.get(key, 0) + quantite

    # Colonnes
    dict_colonnes = {"activites": [], "groupes": [], "unites": []}
    for activite in liste_activites:
        nbre_unites_activite = 0
        liste_groupes_activite = []
        for groupe in dict_groupes.get(activite, []):
            nbre_unites_groupe = 0
            for unite in dict_unites_remplissage.get(activite, []):
                if (unite.pk in unites_ouvertes and (groupe.pk in groupes_ouverts or groupe.pk == 999999)) or not masquer_groupes_fermes:
                    dict_colonnes["unites"].append({"unite": unite, "groupe": groupe, "activite": activite})
                    nbre_unites_activite += 1
                    nbre_unites_groupe += 1
            if groupe.pk in groupes_ouverts or groupe.pk == 999999 or not masquer_groupes_fermes:
                liste_groupes_activite.append({"groupe": groupe, "nbre_colonnes": nbre_unites_groupe})
        if nbre_unites_activite and liste_groupes_activite:
            dict_colonnes["activites"].append({"activite": activite, "nbre_colonnes": nbre_unites_activite})
            dict_colonnes["groupes"] += liste_groupes_activite

    # Récupération des seuils d'alerte
    dict_seuils = {}
    for unite_remplissage in liste_unites_remplissage:
        dict_seuils[unite_remplissage.pk] = unite_remplissage.seuil_alerte

    # Importation des événements
    liste_evenements = Evenement.objects.filter(conditions_periodes & Q(activite__in=liste_activites)).order_by("date", "heure_debut")

    dict_evenements = {}
    dict_all_evenements = {}
    for evenement in liste_evenements:
        for id_unite_remplissage in dict_unites_remplissage_unites.get(evenement.unite_id, []):
            key = "%s_%d_%d" % (evenement.date, id_unite_remplissage, evenement.groupe_id)
            dict_evenements.setdefault(key, [])

            # Recherche les places prises de l'événement
            capacite_max = evenement.capacite_max if evenement.capacite_max else 0
            evenement.prises = dict_places.get(key + "_%d" % evenement.pk, 0)
            evenement.restantes = capacite_max - evenement.prises
            seuil_alerte = dict_seuils[id_unite_remplissage]
            if evenement.restantes <= 0: evenement.classe = "complet"
            elif 0 < evenement.restantes < seuil_alerte: evenement.classe = "dernieresplaces"
            else: evenement.classe = "disponible"
            if mode == "places_initiales": evenement.valeur = capacite_max
            if mode == "places_prises": evenement.valeur = evenement.prises
            if mode == "places_restantes": evenement.valeur = evenement.restantes
            if not evenement.capacite_max:
                evenement.classe = ""
                evenement.restantes = None
                if mode in ("places_initiales", "places_restantes"):
                    evenement.valeur = ""
            dict_evenements[key].append(evenement)
            dict_all_evenements[evenement.pk] = evenement

    dict_cases = {}
    for date in liste_dates:
        for colonne in dict_colonnes["unites"]:
            key_case = "%s_%s_%s" % (date, colonne["unite"].pk, colonne["groupe"].pk)
            case_valide = False
            evenements = dict_evenements.get(key_case, [])

            if colonne["groupe"].pk == 999999:
                # Case TOTAL
                classe = "total"
                initiales = 0
                prises = 0
                restantes = 0
                activite = colonne["activite"]
                for groupe in dict_groupes[activite]:
                    key_temp = "%s_%s_%s" % (date, colonne["unite"].pk, groupe.pk)
                    if key_temp in dict_cases:
                        initiales += dict_cases[key_temp]["initiales"]
                        prises += dict_cases[key_temp]["prises"]
                        restantes += dict_cases[key_temp]["restantes"]
                total_max = dict_capacite.get("%s_%s_0" % (date, colonne["unite"].pk), None)
                if total_max:
                    initiales = total_max
                case_valide = True

            elif key_case in liste_ouvertures:
                # Case normale
                liste_initiales = []
                key = "%s_%s_%s" % (date, colonne["unite"].pk, colonne["groupe"].pk)
                if key in dict_capacite:
                    liste_initiales.append(dict_capacite.get(key, 0))

                initiales = min(liste_initiales) if liste_initiales else 0
                prises = dict_places.get(key_case, 0)
                restantes = initiales - prises
                if restantes < 0:
                    restantes = 0

                # Total max
                key = "%s_%s_0" % (date, colonne["unite"].pk)
                if key in dict_capacite:
                    restantes_total = dict_capacite.get(key, 0) - dict_places.get(key, 0)
                    if not initiales:
                        initiales = dict_capacite.get(key, 0)
                        restantes = restantes_total
                    else:
                        if restantes_total < restantes:
                            restantes = restantes_total

                seuil_alerte = dict_seuils[colonne["unite"].pk]
                if restantes <= 0: classe = "complet"
                elif 0 < restantes < seuil_alerte: classe = "dernieresplaces"
                else: classe = "disponible"
                if not initiales: classe = ""
                case_valide = True

            if case_valide:
                if mode == "places_initiales": valeur = initiales
                if mode == "places_prises": valeur = prises
                if mode == "places_restantes": valeur = restantes
                dict_cases[key_case] = {"initiales": initiales, "prises": prises, "restantes": restantes, "classe": classe, "valeur": valeur, "evenements": evenements}

    data = {
        "dict_cases": dict_cases,
        "dict_evenements": dict_evenements,
        "dict_all_evenements": dict_all_evenements,
        "dict_colonnes": dict_colonnes,
        "liste_vacances": liste_vacances,
        "liste_dates": liste_dates,
        "dict_unites_remplissage_unites": dict_unites_remplissage_unites,
    }
    return data


class View(CustomView, TemplateView):
    menu_code = "suivi_consommations"
    template_name = "consommations/suivi_consommations_view.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Suivi des consommations"
        context['suivi_consommations_parametres'] = Get_parametres(request=self.request)
        return context
