# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.base import CustomView
from django.views.generic import TemplateView
from core.utils import utils_dates, utils_infos_individus, utils_dictionnaires
from individus.forms.liste_inscriptions_attente import Formulaire
from core.models import Inscription, Activite, Groupe
from django.db.models import Q, Count
import json


class View(CustomView, TemplateView):
    menu_code = "liste_inscriptions_attente"
    template_name = "individus/liste_inscriptions_attente.html"
    etat = "attente"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        if self.etat == "attente":
            context['page_titre'] = "Liste des inscriptions en attente"
        else:
            context['page_titre'] = "Liste des inscriptions refusées"
        if "form_parametres" not in kwargs:
            context['form_parametres'] = Formulaire(request=self.request)
            context['resultats'] = json.dumps(self.Get_resultats(parametres={}))
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if form.is_valid() == False:
            return self.render_to_response(self.get_context_data(form_parametres=form))
        context = {
            "form_parametres": form,
            "resultats": json.dumps(self.Get_resultats(parametres=form.cleaned_data)),
        }
        return self.render_to_response(self.get_context_data(**context))

    def Get_resultats(self, parametres={}):
        if not parametres:
            return []

        # Récupération des paramètres
        param_activites = json.loads(parametres["activites"])
        if param_activites["type"] == "groupes_activites":
            condition_activites = Q(activite__groupes_activites__in=param_activites["ids"])
            liste_activites = Activite.objects.filter(groupes_activites__in=param_activites["ids"])
        if param_activites["type"] == "activites":
            condition_activites = Q(activite__in=param_activites["ids"])
            liste_activites = Activite.objects.filter(pk__in=param_activites["ids"])

        # Importation des inscriptions en attente ou refusées
        inscriptions = Inscription.objects.select_related('individu', 'activite', 'groupe', 'categorie_tarif').filter(condition_activites, statut=self.etat)

        dictInscriptions = {}
        dictGroupes = {}
        for inscription in inscriptions:
            utils_dictionnaires.DictionnaireImbrique(dictionnaire=dictInscriptions, cles=[inscription.activite_id, inscription.groupe_id], valeur=[])
            dictTemp = {"IDinscription": inscription.pk, "IDindividu": inscription.individu_id, "nom_individu": inscription.individu.Get_nom(),
                        "date_inscription": inscription.date_debut, "IDactivite": inscription.activite_id, "IDgroupe": inscription.groupe_id,
                        "IDfamille": inscription.famille_id, "nomCategorie": inscription.categorie_tarif.nom}
            dictInscriptions[inscription.activite_id][inscription.groupe_id].append(dictTemp)

            # Mémorisation des groupes
            if (inscription.groupe_id in dictGroupes) == False:
                dictGroupes[inscription.groupe_id] = inscription.groupe.nom

        # Recherche des places disponibles
        dictInscrits = {}
        inscriptions_existantes = Inscription.objects.values("groupe").filter(condition_activites, statut="ok").annotate(nbre=Count('pk'))
        for dict_temp in inscriptions_existantes:
            dictInscrits[dict_temp["groupe"]] = dict_temp["nbre"]

        # Recherche les activités
        dictActivites = {}
        for activite in liste_activites:
            dictActivites[activite.pk] = {"nom": activite.nom, "abrege": activite.abrege, "date_debut": activite.date_debut, "date_fin": activite.date_fin,
                                          "nbre_inscrits_max": activite.nbre_inscrits_max, "groupes": {}}

        # Recherche des groupes
        groupes = Groupe.objects.filter(condition_activites)
        for groupe in groupes:

            # Recherche le nombre d'inscrits sur chaque groupe
            if groupe.pk in dictInscrits:
                nbre_inscrits = dictInscrits[groupe.pk]
            else:
                nbre_inscrits = 0

            # Recherche du nombre de places disponibles sur le groupe
            if groupe.nbre_inscrits_max not in (None, 0):
                nbre_places_disponibles = groupe.nbre_inscrits_max - nbre_inscrits
            else:
                nbre_places_disponibles = None

            # Mémorise le groupe
            dictActivites[groupe.activite_id]["groupes"][groupe.pk] = {"nom": groupe.nom, "nbre_places_disponibles": nbre_places_disponibles,
                                                                       "nbre_inscrits": nbre_inscrits, "nbre_inscrits_max": groupe.nbre_inscrits_max}

        for IDactivite in list(dictActivites.keys()):
            # Recherche le nombre d'inscrits total de l'activité
            dictActivites[IDactivite]["nbre_inscrits"] = 0
            for IDgroupe in dictActivites[IDactivite]["groupes"]:
                if IDgroupe in dictInscrits:
                    dictActivites[IDactivite]["nbre_inscrits"] += dictInscrits[IDgroupe]

            # Recherche du nombre de places disponibles sur l'activité
            if dictActivites[IDactivite]["nbre_inscrits_max"] not in (None, 0):
                dictActivites[IDactivite]["nbre_places_disponibles"] = dictActivites[IDactivite]["nbre_inscrits_max"] - dictActivites[IDactivite]["nbre_inscrits"]
            else:
                dictActivites[IDactivite]["nbre_places_disponibles"] = None

        liste_resultats = []

        # Branches Activités
        listeActivites = list(dictInscriptions.keys())
        listeActivites.sort()

        for IDactivite in listeActivites:
            id_activite = "activite_%s" % IDactivite
            liste_resultats.append({"id": id_activite, "pid": 0, "type": "activite", "label": dictActivites[IDactivite]["nom"], "date_saisie": "", "categorie_tarif": "", "action": ""})

            # Branches Groupes
            listeGroupes = list(dictInscriptions[IDactivite].keys())
            listeGroupes.sort()

            for IDgroupe in listeGroupes:
                id_groupe = "groupe_%s" % IDgroupe
                liste_resultats.append({"id": id_groupe, "pid": id_activite, "type": "groupe", "label": dictGroupes[IDgroupe], "date_saisie": "", "categorie_tarif": "", "action": ""})

                # Branches Inscriptions
                num = 1
                for dictInscription in dictInscriptions[IDactivite][IDgroupe]:
                    texteIndividu = "%d. %s" % (num, dictInscription["nom_individu"])

                    # Recherche si place dispo
                    nbre_places_dispo = self.RechercheSiPlaceDispo(dictActivites[IDactivite], IDgroupe)

                    if nbre_places_dispo == None or nbre_places_dispo > 0:
                        place_dispo = True

                        # Modifie le nombre de places disponibles
                        if dictActivites[IDactivite]["nbre_places_disponibles"] != None:
                            dictActivites[IDactivite]["nbre_places_disponibles"] -= 1
                        if dictActivites[IDactivite]["groupes"][IDgroupe]["nbre_places_disponibles"] != None:
                            dictActivites[IDactivite]["groupes"][IDgroupe]["nbre_places_disponibles"] -= 1
                    else:
                        place_dispo = False

                    # Image
                    if place_dispo == True:
                        label = "<i class='fa fa-check margin-r-5 text-green'></i> %s" % texteIndividu
                    else:
                        label = "<i class='fa fa-remove margin-r-5 text-red'></i> %s" % texteIndividu

                    # URL fiche famille
                    url = reverse("famille_resume", args=[dictInscription["IDfamille"]])
                    action = "<a type='button' class='btn btn-default btn-sm' href='%s' title='Accéder à la fiche famille'><i class='fa fa-folder-open-o'></i></a>" % url

                    # Mémorisation
                    id_inscription = "groupe_%s" % dictInscription["IDinscription"]
                    liste_resultats.append({"id": id_inscription, "pid": id_groupe, "type": "inscription", "label": label,
                                            "date_saisie": utils_dates.DateComplete(dictInscription["date_inscription"]),
                                            "categorie_tarif": dictInscription["nomCategorie"], "action": action})

                    num += 1

        return liste_resultats

    def RechercheSiPlaceDispo(self, dictActivite={}, IDgroupe=None):
        nbre_places_disponibles = []

        if dictActivite["nbre_places_disponibles"] != None:
            nbre_places_disponibles.append(dictActivite["nbre_places_disponibles"])

        for IDgroupeTmp, dictGroupe in dictActivite["groupes"].items():
            if IDgroupeTmp == IDgroupe and dictGroupe["nbre_places_disponibles"] != None:
                nbre_places_disponibles.append(dictGroupe["nbre_places_disponibles"])

        if len(nbre_places_disponibles) > 0:
            return min(nbre_places_disponibles)
        else:
            return None
