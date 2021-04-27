# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.base import CustomView
from django.views.generic import TemplateView
from core.utils import utils_dates, utils_infos_individus, utils_dictionnaires
from consommations.forms.liste_attente import Formulaire
from core.models import Unite, Activite, Evenement, Consommation, Groupe
from django.db.models import Q
import json, datetime
from consommations.views import suivi_consommations


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
            context['form_parametres'] = Formulaire()
            parametres = {"donnees": "periode_reference"}
            context['resultats'] = json.dumps(self.Get_resultats(parametres=parametres))
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST)
        if form.is_valid() == False:
            return self.render_to_response(self.get_context_data(form_parametres=form))
        context = {
            "form_parametres": form,
            "resultats": json.dumps(self.Get_resultats(parametres=form.cleaned_data)),
        }
        return self.render_to_response(self.get_context_data(**context))

    def Get_resultats(self, parametres={}):
        # Utiliser la période de référence
        if parametres["donnees"] == "periode_reference":
            periode_reference = suivi_consommations.Get_parametres()

            # Importation des activités
            condition_activites = Q(activite__in=periode_reference["activites"])
            liste_activites = Activite.objects.filter(pk__in=periode_reference["activites"])

            # Récupération de la période
            listes_dates = []
            if periode_reference["periode"]:
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

        data_remplissage = suivi_consommations.Get_data(parametres={
            "condition_periodes": conditions_periodes,
            "date_min": date_min,
            "date_max": date_max,
            "liste_activites": liste_activites,
        })

        # Importation des consommations en attente
        consommations = Consommation.objects.select_related('unite', 'activite', 'groupe', 'evenement', 'inscription', 'individu').filter(conditions_periodes, condition_activites, etat=self.etat)

        dictConso = {}
        dictActivites = {}
        dictGroupes = {}
        dictIndividus = {}
        dictEvenements = {}
        for conso in consommations:

            # Date
            if (conso.date in dictConso) == False:
                dictConso[conso.date] = {}
            # Activité
            if (conso.activite_id in dictConso[conso.date]) == False:
                dictConso[conso.date][conso.activite_id] = {}
            # Groupe
            if (conso.groupe_id in dictConso[conso.date][conso.activite_id]) == False:
                dictConso[conso.date][conso.activite_id][conso.groupe_id] = {}
            # Evènement
            if (conso.evenement_id in dictConso[conso.date][conso.activite_id][conso.groupe_id]) == False:
                dictConso[conso.date][conso.activite_id][conso.groupe_id][conso.evenement_id] = {}
            # Individu
            if (conso.individu_id in dictConso[conso.date][conso.activite_id][conso.groupe_id][conso.evenement_id]) == False:
                dictConso[conso.date][conso.activite_id][conso.groupe_id][conso.evenement_id][conso.individu_id] = []

            dictTemp = {"IDconso": conso.pk, "IDindividu": conso.individu_id, "IDactivite": conso.activite_id, "date": conso.date, "IDunite": conso.unite_id,
                        "IDgroupe": conso.groupe_id, "etat": conso.etat, "date_saisie": conso.date_saisie, "nomUnite": conso.unite.nom, "ordreUnite": conso.unite.ordre,
                        "IDfamille": conso.inscription.famille_id, "IDevenement": conso.evenement_id, "nomEvenement": conso.evenement.nom if conso.evenement else None}

            dictConso[conso.date][conso.activite_id][conso.groupe_id][conso.evenement_id][conso.individu_id].append(dictTemp)

            if (conso.activite_id in dictActivites) == False:
                dictActivites[conso.activite_id] = conso.activite.nom
            if (conso.groupe_id in dictGroupes) == False:
                dictGroupes[conso.groupe_id] = conso.groupe.nom
            if (conso.individu_id in dictIndividus) == False:
                dictIndividus[conso.individu_id] = {"nomIndividu": conso.individu.Get_nom(), "IDfamille": conso.inscription.famille_id}

            if (conso.evenement_id in dictEvenements) == False and conso.evenement_id != None:
                dictEvenements[conso.evenement_id] = conso.evenement.nom if conso.evenement else None


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
            listeActivites = list(dictConso[date].keys())
            listeActivites.sort()

            for IDactivite in listeActivites:

                id_activite = "%s_activite_%d" % (date, IDactivite)
                if len(listeActivites) > 1:
                    liste_resultats.append({"id": id_activite, "pid": id_date, "type": "activite", "label": dictActivites[IDactivite], "unites": "", "date_saisie": "", "action": ""})
                else:
                    # niveauActivite = niveauDate
                    id_activite = id_date

                # Branches Groupe
                listeGroupes = list(dictConso[date][IDactivite].keys())
                listeGroupes.sort()

                for IDgroupe in listeGroupes:
                    id_groupe = "%s_groupe_%d" % (date, IDgroupe)
                    liste_resultats.append({"id": id_groupe, "pid": id_activite, "type": "groupe", "label": dictGroupes[IDgroupe], "unites": "", "date_saisie": "", "action": ""})

                    # Parcourt les évènements
                    for IDevenement, dictTemp in dictConso[date][IDactivite][IDgroupe].items():

                        id_evenement = "%s_evenement_%d" % (date, IDevenement if IDevenement else 0)
                        if IDevenement != None:
                            liste_resultats.append({"id": id_evenement, "pid": id_groupe, "type": "evenement", "label": dictEvenements[IDevenement], "unites": "", "date_saisie": "", "action": ""})
                        else:
                            id_evenement = id_groupe

                        # Branches Individus
                        listeIndividus = []
                        for IDindividu, listeConso in dictTemp.items():
                            listeIDconso = []
                            for dictConsoIndividu in listeConso:
                                listeIDconso.append(dictConsoIndividu["IDconso"])
                            IDconsoMin = min(listeIDconso)
                            listeIndividus.append((IDconsoMin, IDindividu))
                        listeIndividus.sort()

                        num = 1
                        for ordreIndividu, IDindividu in listeIndividus:
                            nomIndividu = dictIndividus[IDindividu]["nomIndividu"]
                            texteIndividu = u"%d. %s" % (num, nomIndividu)
                            IDfamille = dictIndividus[IDindividu]["IDfamille"]

                            # Détail pour l'individu
                            texteUnites = ""
                            dateSaisie = None
                            placeDispo = True
                            listePlaces = []
                            for dictUnite in dictConso[date][IDactivite][IDgroupe][IDevenement][IDindividu]:

                                IDunite = dictUnite["IDunite"]
                                date_saisie = dictUnite["date_saisie"]
                                nomUnite = dictUnite["nomUnite"]
                                if IDevenement != None:
                                    nomUnite += " (%s)" % dictEvenements[IDevenement]
                                texteUnites += nomUnite + " + "
                                if dateSaisie == None or date_saisie < dateSaisie:
                                    dateSaisie = date_saisie

                                # Etat des places
                                key_case = "%s_%s_%s" % (date, IDunite, IDgroupe)
                                case = data_remplissage["dict_cases"].get(key_case)
                                if case:
                                    nbrePlacesRestantes = case["restantes"]
                                    if IDunite in data_remplissage["dict_unites_remplissage_unites"]:
                                        for IDuniteRemplissage in data_remplissage["dict_unites_remplissage_unites"][IDunite]:
                                            key = (date, IDactivite, IDgroupe, IDuniteRemplissage, IDevenement)
                                            nbrePlacesRestantes -= dictPlacesRestantes.get(key, 0)
                                    if nbrePlacesRestantes <= 0:
                                        placeDispo = False

                            # S'il reste finalement une place dispo, on change le nbre de places restantes
                            if placeDispo == True:
                                for dictUnite in dictConso[date][IDactivite][IDgroupe][IDevenement][IDindividu]:
                                    IDunite = dictUnite["IDunite"]
                                    if IDunite in data_remplissage["dict_unites_remplissage_unites"]:
                                        for IDuniteRemplissage in data_remplissage["dict_unites_remplissage_unites"][IDunite]:
                                            key = (date, IDactivite, IDgroupe, IDuniteRemplissage, IDevenement)
                                            dictPlacesRestantes.setdefault(key, 0)
                                            dictPlacesRestantes[key] += 1

                            # Icone
                            if placeDispo == True:
                                label = "<i class='fa fa-check margin-r-5 text-green'></i> %s" % texteIndividu
                            else:
                                label = "<i class='fa fa-remove margin-r-5 text-red'></i> %s" % texteIndividu

                            # URL fiche famille
                            action = " ".join([
                                "<a type='button' title='Accéder à la fiche famille' class='btn btn-default btn-xs' href='%s'><i class='fa fa-folder-open-o'></i></a>" % reverse("famille_resume", args=[IDfamille]),
                                "<a type='button' title='Accéder aux consommations' class='btn btn-default btn-xs' href='%s'><i class='fa fa-fw fa-calendar'></i></a>" % reverse("famille_consommations", args=[IDfamille, IDindividu]),
                            ])

                            liste_resultats.append({
                                "id": "individu_%s" % IDindividu, "pid": id_evenement, "type": "individu", "label": label, "idfamille": IDfamille, "idindividu": IDindividu,
                                "unites": texteUnites[:-3], "date_saisie": utils_dates.DateComplete(dateSaisie), "action": action
                            })

                            num += 1

        return liste_resultats
