# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.views.generic import TemplateView
from django.contrib import messages
from django.http import JsonResponse
from core.models import Activite, Unite, UniteRemplissage, Groupe, Ouverture, Remplissage, Vacance, Ferie, Consommation, Evenement
from parametrage.forms.activites_ouvertures import Formulaire, Form_lot
from parametrage.views.activites import Onglet
from core.utils import utils_dates, utils_db
from django.db.models import Q
from django.shortcuts import render
import datetime, calendar, json


class Groupe_total():
    def __init__(self):
        self.pk = 0
        self.nom = "Total"


def Get_calendrier_ouvertures(request=None):
    mois = int(request.POST.get("mois"))+1
    annee = int(request.POST.get("annee"))
    idactivite = int(request.POST.get("idactivite"))

    # Calcule les dates du mois
    tmp, nbreJours = calendar.monthrange(annee, mois)
    liste_dates_tmp = []
    for numJour in range(1, nbreJours + 1):
        date = datetime.date(annee, mois, numJour)
        liste_dates_tmp.append(date)

    date_min = datetime.date(annee, mois, 1)
    date_max = date

    # Importe les données sur l'activité
    liste_unites = Unite.objects.filter(activite_id=idactivite).order_by("ordre")
    liste_unites_remplissage = UniteRemplissage.objects.filter(activite_id=idactivite).order_by("ordre")
    liste_groupes = list(Groupe.objects.filter(activite_id=idactivite).order_by("ordre")) + [Groupe_total,]
    liste_ouvertures = Ouverture.objects.filter(activite_id=idactivite, date__gte=date_min, date__lte=date_max)
    liste_remplissage = Remplissage.objects.filter(activite_id=idactivite, date__gte=date_min, date__lte=date_max)
    liste_vacances = Vacance.objects.filter(date_fin__gte=date_min, date_debut__lte=date_max)
    liste_feries = Ferie.objects.filter(mois=mois).filter(Q(annee=0) | Q(annee=annee))
    liste_conso = Consommation.objects.filter(activite_id=idactivite, date__gte=date_min, date__lte=date_max)
    liste_evenements = Evenement.objects.filter(activite_id=idactivite, date__gte=date_min, date__lte=date_max)

    # Regroupement des consommations
    dict_conso = {}
    for conso in liste_conso:
        key = "ouverture_%s_%d_%d" % (conso.date, conso.groupe_id, conso.unite_id)
        if key not in dict_conso:
            dict_conso[key] = 0
        dict_conso[key] += 1

    # Création de la liste de dates complète
    liste_dates = []
    for date in liste_dates_tmp:
        liste_dates.append({
            "date": date,
            "vacance": utils_dates.EstEnVacances(date, liste_vacances),
            "ferie": utils_dates.EstFerie(date, liste_feries),
        })

    # Création des dict
    dict_ouvertures = {}
    for ouverture in liste_ouvertures:
        key = "ouverture_%s_%d_%d" % (ouverture.date, ouverture.groupe_id, ouverture.unite_id)
        dict_ouvertures[key] = True

    dict_evenements = {}
    for evenement in liste_evenements:
        key = "ouverture_%s_%d_%d" % (evenement.date, evenement.groupe_id, evenement.unite_id)
        if key not in dict_evenements:
            dict_evenements[key] = 0
        dict_evenements[key] += 1

    dict_remplissage = {}
    for remplissage in liste_remplissage:
        if not remplissage.groupe_id: remplissage.groupe_id = 0
        key = "remplissage_%s_%d_%d" % (remplissage.date, remplissage.groupe_id, remplissage.unite_remplissage_id)
        dict_remplissage[key] = remplissage.places

    context = {
        "dates": liste_dates, "unites": liste_unites, "groupes": liste_groupes, "unites_remplissage": liste_unites_remplissage,
        "ouvertures": dict_ouvertures, "remplissages": dict_remplissage, "dict_conso": dict_conso, "dict_evenements": dict_evenements,
        "update": True,
    }

    return render(request, 'parametrage/widgets/calendrier_ouvertures.html', context)


class Modifier(Onglet, TemplateView):
    template_name = "parametrage/activite_ouvertures.html"

    def get_context_data(self, **kwargs):
        context = super(Modifier, self).get_context_data(**kwargs)
        context['box_titre'] = "Calendrier"
        context['box_introduction'] = "Cliquez sur les cases des unités de consommation pour les ouvrir et saisissez la capacité maximale par groupe dans les cases des unités de remplissage."
        context['onglet_actif'] = "calendrier"
        context['form'] = Formulaire
        context['form_lot'] = Form_lot
        return context



def FormateErreursForm(form):
    texte_erreurs = ""
    for field in form.visible_fields():
        if field.errors:
            texte_erreurs += "<p><b>%s</b> : %s</p>" % (field.label, ", ".join(field.errors))
    return """
    <div class="alert alert-danger alert-dismissible">
        <button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button>
        %s
    </div>
    """ % texte_erreurs




def Traitement_lot_ouvertures(request):
    form = Form_lot(request.POST)

    # Validation du formulaire
    if form.is_valid() == False:
        return JsonResponse({"erreur": FormateErreursForm(form)}, status=401)

    # Récupération des données du formulaire
    idactivite = int(request.POST.get("idactivite"))
    action = request.POST.get("action_type")
    date_modele = request.POST.get("date_modele")
    date_debut = request.POST.get("date_debut")
    date_fin = request.POST.get("date_fin")
    jours_scolaires = request.POST.getlist("jours_scolaires")
    jours_vacances = request.POST.getlist("jours_vacances")
    semaines = request.POST.get("frequence_type")
    ouvertures_modifications = json.loads(request.POST.get("ouvertures_modifications"))
    remplissages_modifications = json.loads(request.POST.get("remplissages_modifications"))
    feries = request.POST.get("inclure_feries") == "on"

    # Formatage des dates
    if date_modele:
        date_modele = utils_dates.ConvertDateFRtoDate(date_modele)
    date_debut = utils_dates.ConvertDateFRtoDate(date_debut)
    date_fin = utils_dates.ConvertDateFRtoDate(date_fin)

    # Importe les données sur l'activité
    date_debut_temp = date_debut
    date_fin_temp = date_fin
    if date_modele:
        if date_modele < date_debut_temp:
            date_debut_temp = date_modele
        if date_modele > date_fin_temp:
            date_fin_temp = date_modele

    liste_unites = Unite.objects.filter(activite_id=idactivite).order_by("ordre")
    liste_unites_remplissage = UniteRemplissage.objects.filter(activite_id=idactivite).order_by("ordre")
    liste_groupes = Groupe.objects.filter(activite_id=idactivite).order_by("ordre")
    liste_vacances = Vacance.objects.filter(date_fin__gte=date_debut_temp, date_debut__lte=date_fin_temp)
    liste_feries = Ferie.objects.all()
    liste_conso = Consommation.objects.filter(activite_id=idactivite, date__gte=date_debut_temp, date__lte=date_fin_temp)
    liste_ouvertures = Ouverture.objects.filter(activite_id=idactivite, date__gte=date_debut_temp, date__lte=date_fin_temp)
    liste_remplissage = Remplissage.objects.filter(activite_id=idactivite, date__gte=date_debut_temp, date__lte=date_fin_temp)

    # Création des dict
    dict_ouvertures = {}
    for ouverture in liste_ouvertures:
        key = "ouverture_%s_%d_%d" % (ouverture.date, ouverture.groupe_id, ouverture.unite_id)
        dict_ouvertures[key] = True

    dict_remplissage = {}
    for remplissage in liste_remplissage:
        key = "remplissage_%s_%d_%d" % (remplissage.date, remplissage.groupe_id or 0, remplissage.unite_remplissage_id)
        dict_remplissage[key] = remplissage.places

    # Regroupement des consommations
    dict_conso = {}
    for conso in liste_conso:
        key = "ouverture_%s_%d_%d" % (conso.date, conso.groupe_id, conso.unite_id)
        if key not in dict_conso: dict_conso[key] = 0
        dict_conso[key] += 1

    # Liste dates
    listeDates = [date_debut,]
    tmp = date_debut
    while tmp < date_fin:
        tmp += datetime.timedelta(days=1)
        listeDates.append(tmp)


    date = date_debut
    numSemaine = int(semaines)
    dateTemp = date
    for date in listeDates:

        # Vérifie période et jour
        valide = False
        if utils_dates.EstEnVacances(date, liste_vacances):
            if str(date.weekday()) in jours_vacances:
                valide = True
        else:
            if str(date.weekday()) in jours_scolaires:
                valide = True

        # Calcul le numéro de semaine
        if len(listeDates) > 0:
            if date.weekday() < dateTemp.weekday():
                numSemaine += 1

        # Fréquence semaines
        if semaines in (2, 3, 4):
            if numSemaine % semaines != 0:
                valide = False

        # Semaines paires et impaires
        if valide == True and semaines in (5, 6):
            numSemaineAnnee = date.isocalendar()[1]
            if numSemaineAnnee % 2 == 0 and semaines == 6:
                valide = False
            if numSemaineAnnee % 2 != 0 and semaines == 5:
                valide = False

        # Vérifie si férié
        if feries == False and utils_dates.EstFerie(date, liste_feries):
            valide = False

        # Application
        if valide == True:

            for idgroupe in [0] + [groupe.pk for groupe in liste_groupes]:

                # Ouvertures
                if action in ("COPIER_DATE", "schema", "REINIT") and idgroupe:

                    for unite in liste_unites:
                        key = "ouverture_%s_%d_%d" % (date, idgroupe, unite.pk)

                        etat = False
                        if action == "COPIER_DATE":
                            key_modele = "ouverture_%s_%d_%d" % (date_modele, idgroupe, unite.pk)
                            if key_modele in dict_ouvertures:
                                etat = dict_ouvertures[key_modele]
                            if key_modele in ouvertures_modifications:
                                etat = ouvertures_modifications[key_modele]

                        # Vérifie si pas de conso
                        nbreConso = dict_conso.get(key, 0)

                        if nbreConso == 0:
                            ouvertures_modifications[key] = etat

                # Remplissage
                if action in ("COPIER_DATE", "schema", "REINIT"):

                    for uniteRemplissage in liste_unites_remplissage:
                        key = "remplissage_%s_%d_%d" % (date, idgroupe, uniteRemplissage.pk)

                        nbrePlaces = ""
                        if action == "COPIER_DATE":
                            key_modele = "remplissage_%s_%d_%d" % (date_modele, idgroupe, uniteRemplissage.pk)
                            if key_modele in dict_remplissage:
                                nbrePlaces = dict_remplissage[key_modele]
                            if key_modele in remplissages_modifications:
                                nbrePlaces = remplissages_modifications[key_modele]

                        # Mémorise remplissage
                        remplissages_modifications[key] = nbrePlaces

        dateTemp = date

    dict_resultats = {"success": True, "ouvertures_modifications": ouvertures_modifications, "remplissages_modifications": remplissages_modifications}
    return JsonResponse(dict_resultats)



def Valider_calendrier_ouvertures(request):
    # Récupération des données du formulaire
    idactivite = int(request.POST.get("idactivite"))
    ouvertures_modifications = json.loads(request.POST.get("ouvertures_modifications"))
    remplissages_modifications = json.loads(request.POST.get("remplissages_modifications"))

    # Importe les données sur l'activité
    liste_unites = Unite.objects.filter(activite_id=idactivite).order_by("ordre")
    liste_unites_remplissage = UniteRemplissage.objects.filter(activite_id=idactivite).order_by("ordre")
    liste_groupes = Groupe.objects.filter(activite_id=idactivite).order_by("ordre")

    # Mémorise sous forme de dict les données
    dict_groupes = {}
    for groupe in liste_groupes:
        dict_groupes[groupe.pk] = groupe

    dict_unites = {}
    for unite in liste_unites:
        dict_unites[unite.pk] = unite

    dict_unites_remplissage = {}
    for unite_remplissage in liste_unites_remplissage:
        dict_unites_remplissage[unite_remplissage.pk] = unite_remplissage

    # Importe les ouvertures et remplissages existants
    dict_temp = dict(ouvertures_modifications)
    dict_temp.update(remplissages_modifications)
    if len(dict_temp) > 0:
        date_min = utils_dates.ConvertDateENGtoDate(min(dict_temp.keys()).split("_")[1])
        date_max = utils_dates.ConvertDateENGtoDate(max(dict_temp.keys()).split("_")[1])
        liste_ouvertures = Ouverture.objects.filter(activite_id=idactivite, date__gte=date_min, date__lte=date_max)
        liste_remplissages = Remplissage.objects.filter(activite_id=idactivite, date__gte=date_min, date__lte=date_max)
    else:
        liste_ouvertures = []
        liste_remplissages = []

    # Suppression des ouvertures
    dict_ouvertures_existantes = {}
    liste_suppressions = []
    for ouverture in liste_ouvertures:
        # Mémorisation pour ajout
        key = "ouverture_%s_%d_%d" % (ouverture.date, ouverture.groupe_id, ouverture.unite_id)
        dict_ouvertures_existantes[key] = ouverture
        # Suppression
        if ouvertures_modifications.get(key, None) == False:
            liste_suppressions.append(ouverture.pk)

    if liste_suppressions:
        qs = Ouverture.objects.filter(pk__in=liste_suppressions)
        qs._raw_delete(qs.db)

    # Ajout des ouvertures
    liste_ajouts = []
    for key, valeur in ouvertures_modifications.items():
        if valeur != False and key not in dict_ouvertures_existantes:
            categorie, date, idgroupe, idunite = key.split("_")
            ouverture = Ouverture(
                activite_id=idactivite,
                unite=dict_unites[int(idunite)],
                groupe=dict_groupes[int(idgroupe)],
                date=utils_dates.ConvertDateENGtoDate(date),
            )
            liste_ajouts.append(ouverture)

    if liste_ajouts:
        Ouverture.objects.bulk_create(liste_ajouts)

    # Suppression des remplissages
    dict_remplissages_existants = {}
    liste_suppressions = []
    for remplissage in liste_remplissages:
        # Mémorisation pour ajout
        if not remplissage.groupe_id: remplissage.groupe_id = 0
        key = "remplissage_%s_%d_%d" % (remplissage.date, remplissage.groupe_id, remplissage.unite_remplissage_id)
        dict_remplissages_existants[key] = remplissage
        # Suppression
        if remplissages_modifications.get(key, "XXX") in (0, "", None):
            liste_suppressions.append(remplissage.pk)

    if liste_suppressions:
        qs = Remplissage.objects.filter(pk__in=liste_suppressions)
        qs._raw_delete(qs.db)

    # Ajout et modification des remplissages
    liste_ajouts = []
    liste_modifications = []
    for key, valeur in remplissages_modifications.items():
        if valeur not in (0, "", None):
            # Ajout
            if key not in dict_remplissages_existants:
                categorie, date, idgroupe, idunite_remplissage = key.split("_")
                remplissage = Remplissage(
                    activite_id=idactivite,
                    unite_remplissage=dict_unites_remplissage[int(idunite_remplissage)],
                    groupe=dict_groupes[int(idgroupe)] if int(idgroupe) != 0 else None,
                    date=utils_dates.ConvertDateENGtoDate(date),
                    places=valeur,
                )
                liste_ajouts.append(remplissage)
            # Modification
            else:
                remplissage = dict_remplissages_existants[key]
                if valeur != remplissage.places:
                    remplissage.places = valeur
                    liste_modifications.append(remplissage)

    if liste_ajouts:
        Remplissage.objects.bulk_create(liste_ajouts)
    if liste_modifications:
        Remplissage.objects.bulk_update(liste_modifications, ['places'])

    messages.add_message(request, messages.SUCCESS, 'Modification enregistrée')

    dict_resultats = {"success": True}
    return JsonResponse(dict_resultats)
