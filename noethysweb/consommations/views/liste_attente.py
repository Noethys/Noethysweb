# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, datetime
from django.urls import reverse_lazy, reverse
from django.views.generic import TemplateView
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.core.exceptions import PermissionDenied
from core.views.base import CustomView
from core.utils import utils_dates, utils_infos_individus, utils_dictionnaires
from core.models import Unite, Activite, Evenement, Consommation, Groupe
from consommations.views import suivi_consommations
from consommations.forms.liste_attente import Formulaire


def Traitement_automatique(request):
    """ Traitement automatique des places disponibles à réattribuer """
    if getattr(request.user, "categorie", None) != "utilisateur":
        raise PermissionDenied()

    from consommations.utils import utils_traitement_attentes
    utils_traitement_attentes.Traiter_attentes(request=request)
    return HttpResponseRedirect(reverse_lazy("liste_attente"))


def Attribution_manuelle(request):
    """ Attribution manuelle des places sélectionnées """
    selections = json.loads(request.POST.get("selections"))
    from consommations.utils import utils_traitement_attentes
    utils_traitement_attentes.Traiter_attentes(request=request, selections=selections)
    return JsonResponse({"resultat": True})


class View(CustomView, TemplateView):
    menu_code = "liste_attente"
    template_name = "consommations/liste_attente.html"
    etat = "attente"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        if self.etat == "attente":
            context['page_titre'] = "Liste d'attente"
        else:
            context['page_titre'] = "Liste des places refusées"
        if "form_parametres" not in kwargs:
            context['form_parametres'] = Formulaire(request=self.request)
            parametres = {"donnees": "periode_reference"}
            liste_resultats = Get_resultats(parametres=parametres, etat=self.etat, request=self.request)
            context['resultats'] = json.dumps(liste_resultats)
            context['nbre_disponibilites'] = len([1 for resultat in liste_resultats if resultat.get("place_dispo", False)])
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if form.is_valid() == False:
            return self.render_to_response(self.get_context_data(form_parametres=form))
        context = {
            "form_parametres": form,
            "resultats": json.dumps(Get_resultats(parametres=form.cleaned_data, etat=self.etat, request=self.request)),
        }
        return self.render_to_response(self.get_context_data(**context))


def Get_resultats(parametres={}, etat="attente", request=None):
    # Utiliser la période de référence
    if parametres["donnees"] == "periode_reference":
        periode_reference = suivi_consommations.Get_parametres(request=request)

        # Importation des activités
        condition_activites = Q(activite__in=periode_reference["activites"])
        liste_activites = Activite.objects.filter(pk__in=periode_reference["activites"])

        # Récupération de la période
        listes_dates = []
        if periode_reference["periode"] and periode_reference["periode"].get("periodes", None):
            conditions_periodes = Q()
            for p in periode_reference["periode"]["periodes"]:
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

    # Utiliser des paramètres définis
    if parametres["donnees"] == "periode_definie":
        date_min = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[0])
        date_max = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[1])
        param_activites = json.loads(parametres["activites"])
        conditions_periodes = Q(date__gte=date_min) & Q(date__lte=date_max)
        if param_activites["type"] == "groupes_activites":
            condition_activites = Q(activite__groupes_activites__in=param_activites["ids"])
            liste_activites = Activite.objects.filter(groupes_activites__in=param_activites["ids"])
        if param_activites["type"] == "activites":
            condition_activites = Q(activite__in=param_activites["ids"])
            liste_activites = Activite.objects.filter(pk__in=param_activites["ids"])

    # Paramètres spéciaux pour envoi des attentes par email
    if parametres["donnees"] == "traitement_attente":
        date_min = parametres["date_min"]
        date_max = parametres["date_max"]
        conditions_periodes = Q(date__gte=date_min) & Q(date__lte=date_max)
        liste_activites = parametres["activites"]
        condition_activites = Q(activite__in=liste_activites)

    # Récupération du remplissage
    data_remplissage = suivi_consommations.Get_data(request=request, parametres={
        "condition_periodes": conditions_periodes,
        "date_min": date_min,
        "date_max": date_max,
        "liste_activites": liste_activites,
    })

    # Importation des consommations en attente
    consommations = Consommation.objects.select_related('unite', 'activite', 'groupe', 'evenement', 'inscription', 'individu', "inscription__individu").filter(conditions_periodes, condition_activites, etat=etat)

    dictConso = {}
    for conso in consommations:

        utils_dictionnaires.DictionnaireImbrique(dictionnaire=dictConso, cles=[conso.date, conso.activite, conso.groupe, conso.evenement, conso.inscription], valeur=[])

        dictTemp = {"IDconso": conso.pk, "IDindividu": conso.individu_id, "IDactivite": conso.activite_id, "date": conso.date, "IDunite": conso.unite_id,
                    "IDgroupe": conso.groupe_id, "etat": conso.etat, "date_saisie": conso.date_saisie, "nomUnite": conso.unite.nom, "ordreUnite": conso.unite.ordre,
                    "IDfamille": conso.inscription.famille_id, "IDevenement": conso.evenement_id, "nom_activite": conso.activite.nom, "inscription": conso.inscription,
                    "nomEvenement": conso.evenement.nom if conso.evenement else None}

        dictConso[conso.date][conso.activite][conso.groupe][conso.evenement][conso.inscription].append(dictTemp)

    # Remplissage
    dictPlacesRestantes = {}

    # Branches DATE
    listeDates = list(dictConso.keys())
    listeDates.sort()

    liste_resultats = []

    for date in listeDates:
        id_date = str(date)
        liste_resultats.append({"id": id_date, "pid": 0, "type": "date", "label": utils_dates.DateComplete(date), "unites": "", "date_saisie": "", "action": ""})

        # Branches Activités
        listeActivites = sorted(list(dictConso[date].keys()), key=lambda activite: activite.nom)

        for activite in listeActivites:

            id_activite = "%s_activite_%d" % (date, activite.pk)
            if len(listeActivites) > 1:
                liste_resultats.append({"id": id_activite, "pid": id_date, "type": "activite", "label": activite.nom, "unites": "", "date_saisie": "", "action": ""})
            else:
                id_activite = id_date

            # Branches Groupe
            listeGroupes = sorted(list(dictConso[date][activite].keys()), key=lambda groupe: groupe.nom)

            for groupe in listeGroupes:
                id_groupe = "%s_groupe_%d" % (date, groupe.pk)
                label_groupe = groupe.nom if len(listeActivites) > 1 else "%s - %s" % (activite.nom, groupe.nom)
                liste_resultats.append({"id": id_groupe, "pid": id_activite, "type": "groupe", "label": label_groupe, "unites": "", "date_saisie": "", "action": ""})

                # Parcourt les évènements
                for evenement, dictTemp in dictConso[date][activite][groupe].items():

                    id_evenement = "%s_evenement_%d" % (date, evenement.pk if evenement else 0)
                    if evenement:
                        liste_resultats.append({"id": id_evenement, "pid": id_groupe, "type": "evenement", "label": evenement.nom, "unites": "", "date_saisie": "", "action": ""})
                    else:
                        id_evenement = id_groupe

                    # Branches inscriptions
                    listeInscriptions = [(min([dictConsoIndividu["IDconso"] for dictConsoIndividu in listeConso]), inscription) for inscription, listeConso in dictTemp.items()]
                    listeInscriptions.sort()

                    num = 1
                    for ordreIndividu, inscription in listeInscriptions:
                        texteIndividu = "%d. %s" % (num, inscription.individu.Get_nom())

                        # Détail pour l'individu
                        texteUnites = ""
                        dateSaisie = None
                        placeDispo = True
                        listeIDunite = []
                        listeIDconso = []
                        for dictUnite in dictConso[date][activite][groupe][evenement][inscription]:

                            IDunite = dictUnite["IDunite"]
                            date_saisie = dictUnite["date_saisie"]
                            nomUnite = dictUnite["nomUnite"]
                            if evenement:
                                nomUnite = evenement.nom
                            texteUnites += nomUnite + " + "
                            if dateSaisie == None or date_saisie < dateSaisie:
                                dateSaisie = date_saisie

                            # Etat des places
                            if evenement and evenement.capacite_max:
                                nbre_places_restantes = data_remplissage["dict_all_evenements"][evenement.pk].restantes if evenement.pk in data_remplissage["dict_all_evenements"] else 0
                                if nbre_places_restantes <= 0:
                                    placeDispo = False
                                if placeDispo:
                                    data_remplissage["dict_all_evenements"][evenement.pk].restantes -= 1

                            else:
                                listePlacesRestantes = []
                                if IDunite in data_remplissage["dict_unites_remplissage_unites"]:
                                    for IDuniteRemplissage in data_remplissage["dict_unites_remplissage_unites"][IDunite]:

                                        # Récupère les places restantes du suivi des conso
                                        key_unite_remplissage = "%s_%s_%s" % (date, IDuniteRemplissage, groupe.pk)
                                        dict_places_unite_remplissage = data_remplissage["dict_cases"].get(key_unite_remplissage, None)

                                        # Enlève les places réattribuées
                                        if dict_places_unite_remplissage and dict_places_unite_remplissage["initiales"] > 0:
                                            nbre_places_restantes = None
                                            if evenement:
                                                for evenement_tmp in dict_places_unite_remplissage["evenements"]:
                                                    if evenement_tmp.pk == evenement.pk:
                                                        nbre_places_restantes = evenement_tmp.restantes
                                            else:
                                                nbre_places_restantes = dict_places_unite_remplissage["restantes"]

                                            key = (date, activite, groupe, IDuniteRemplissage, evenement)
                                            if nbre_places_restantes is not None:
                                                nbre_places_restantes -= dictPlacesRestantes.get(key, 0)
                                                listePlacesRestantes.append(nbre_places_restantes)

                                if listePlacesRestantes and min(listePlacesRestantes) <= 0:
                                    placeDispo = False

                        # S'il reste finalement une place dispo, on change le nbre de places restantes
                        if placeDispo:
                            for dictUnite in dictConso[date][activite][groupe][evenement][inscription]:
                                IDunite = dictUnite["IDunite"]
                                listeIDunite.append(IDunite)
                                listeIDconso.append(dictUnite["IDconso"])
                                if IDunite in data_remplissage["dict_unites_remplissage_unites"]:
                                    for IDuniteRemplissage in data_remplissage["dict_unites_remplissage_unites"][IDunite]:
                                        key = (date, activite, groupe, IDuniteRemplissage, evenement)
                                        dictPlacesRestantes.setdefault(key, 0)
                                        dictPlacesRestantes[key] += 1

                        # Icone
                        if placeDispo:
                            label = "<i class='fa fa-check margin-r-5 text-green'></i> %s <small class='badge badge-pill badge-success'>Disponible</small>" % texteIndividu
                        else:
                            label = "<i class='fa fa-remove margin-r-5 text-red'></i> %s" % texteIndividu

                        # URL fiche famille
                        action = " ".join([
                            "<a type='button' title='Accéder à la fiche famille' class='btn btn-default btn-xs' href='%s'><i class='fa fa-folder-open-o'></i></a>" % reverse("famille_resume", args=[inscription.famille_id]),
                            "<a type='button' title='Accéder aux consommations' class='btn btn-default btn-xs' href='%s'><i class='fa fa-fw fa-calendar'></i></a>" % reverse("famille_consommations", args=[inscription.famille_id, inscription.individu_id]),
                        ])

                        liste_resultats.append({
                            "id": "individu_%s" % inscription.individu_id, "pid": id_evenement, "type": "individu", "label": label, "idfamille": inscription.famille_id, "idindividu": inscription.individu_id,
                            "unites": texteUnites[:-3], "date_saisie": utils_dates.DateComplete(dateSaisie), "action": action, "idactivite": activite.pk,
                            "liste_IDunite": listeIDunite, "date": str(date), "place_dispo": placeDispo, "nom_activite": activite.nom, "liste_IDconso": listeIDconso,
                        })

                        num += 1

    return liste_resultats
