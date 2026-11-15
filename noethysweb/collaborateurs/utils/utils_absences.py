# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Absences des collaborateurs vues depuis le planning : planning des absences et éléments variables de paie.
    Une absence est un évènement d'une catégorie liée à un type de congé, d'une catégorie en temps soustrait
    ou d'une catégorie en temps non comptabilisé prise en compte dans l'objectif (congés, maladie...). """

import datetime
from django.db.models import Q
from core.models import EvenementCollaborateur, TypeEvenementCollaborateur, TypeCongeCollaborateur
from collaborateurs.utils import utils_conges

MIDI = 12 * 60
TREIZE_HEURES = 13 * 60


def Get_categories_absence():
    """ Catégories d'évènements considérées comme des absences : {idcategorie: categorie} """
    ids_conges = set(TypeCongeCollaborateur.objects.values_list("categorie_id", flat=True))
    conditions = Q(pk__in=ids_conges) | Q(type="SOUSTRACTION") | (Q(type="NEUTRE") & ~Q(temps_travail_objectif="NON"))
    return {categorie.pk: categorie for categorie in TypeEvenementCollaborateur.objects.filter(conditions).order_by("nom")}


def Get_minutes_par_jour(collaborateurs=[], date_debut=None, date_fin=None, categories=[]):
    """ Minutes d'absence par collaborateur, jour et catégorie, avec l'heure de début et de fin de l'absence dans la journée.
        Renvoie {(idcollaborateur, date): {idcategorie: {"minutes", "debut", "fin"}}} (debut et fin en minutes depuis minuit). """
    debut_periode = datetime.datetime.combine(date_debut, datetime.time(0))
    fin_periode = datetime.datetime.combine(date_fin + datetime.timedelta(days=1), datetime.time(0))
    resultats = {}
    for evenement in EvenementCollaborateur.objects.filter(collaborateur_id__in=collaborateurs, type_evenement_id__in=categories,
                                                          date_debut__lt=fin_periode, date_fin__gt=debut_periode):
        date = max(evenement.date_debut, debut_periode).date()
        while datetime.datetime.combine(date, datetime.time(0)) < min(evenement.date_fin, fin_periode):
            jour = datetime.datetime.combine(date, datetime.time(0))
            debut = max(evenement.date_debut, jour)
            fin = min(evenement.date_fin, jour + datetime.timedelta(days=1))
            minutes = (fin - debut).total_seconds() / 60
            if minutes > 0:
                valeurs = resultats.setdefault((evenement.collaborateur_id, date), {}).setdefault(evenement.type_evenement_id, {"minutes": 0, "debut": 1440, "fin": 0})
                valeurs["minutes"] += minutes
                valeurs["debut"] = min(valeurs["debut"], (debut - jour).total_seconds() / 60)
                valeurs["fin"] = max(valeurs["fin"], (fin - jour).total_seconds() / 60)
            date += datetime.timedelta(days=1)
    return resultats


def Portion_journee(minutes=0, debut=0, fin=0, minutes_reference=0):
    """ JOURNEE, MATIN ou APRES_MIDI selon la durée de l'absence par rapport à une journée de travail du collaborateur """
    if minutes >= utils_conges.SEUIL_JOURNEE * minutes_reference:
        return "JOURNEE"
    if fin <= TREIZE_HEURES:
        return "MATIN"
    if debut >= MIDI:
        return "APRES_MIDI"
    return "MATIN" if (MIDI - debut) >= (fin - MIDI) else "APRES_MIDI"


def Get_jours_demande(demande=None, contrats=[], liste_feries=[]):
    """ Jours d'une demande d'absence (non encore validée) : {date: JOURNEE | MATIN | APRES_MIDI}, sur les jours habituellement travaillés """
    jours = {}
    if demande.heure_debut and demande.heure_fin:
        debut = demande.heure_debut.hour * 60 + demande.heure_debut.minute
        fin = demande.heure_fin.hour * 60 + demande.heure_fin.minute
        jours[demande.date_debut] = Portion_journee(fin - debut, debut, fin, utils_conges.Minutes_reference(contrats, demande.date_debut))
        return jours
    date = demande.date_debut
    while date <= demande.date_fin:
        if utils_conges.Est_travaille(date, contrats, liste_feries):
            if date == demande.date_debut and demande.debut_apres_midi:
                jours[date] = "APRES_MIDI"
            elif date == demande.date_fin and demande.fin_matin:
                jours[date] = "MATIN"
            else:
                jours[date] = "JOURNEE"
        date += datetime.timedelta(days=1)
    return jours
