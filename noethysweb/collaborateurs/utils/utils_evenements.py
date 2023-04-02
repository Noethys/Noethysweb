# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from dateutil import rrule
from core.utils import utils_dates
from core.models import LigneModelePlanningCollaborateur, EvenementCollaborateur, ContratCollaborateur, Vacance, Ferie


def Is_evenement_in_contrat(evenement=None, contrats=[]):
    """ Vérifie si un évènement est bien compris dans un contrat """
    for contrat in contrats:
        if not contrat.date_fin and evenement.date_debut.date() >= contrat.date_debut:
            return True
        if contrat.date_fin and evenement.date_debut.date() >= contrat.date_debut and evenement.date_fin.date() <= contrat.date_fin:
            return True
    return False


def Generation_evenements(idcollaborateur=None, modeles=[], date_debut=None, date_fin=None):
    """ Application de modèles de planning à un collaborateur """
    # Importation des données diverses
    liste_vacances = Vacance.objects.all()
    liste_feries = Ferie.objects.all()
    jours_rrule = [rrule.MO, rrule.TU, rrule.WE, rrule.TH, rrule.FR, rrule.SA, rrule.SU]

    # Recherche des évènements à créer
    liste_evenements = []
    for modele in modeles:
        for evenement_modele in LigneModelePlanningCollaborateur.objects.select_related("type_evenement").filter(modele=modele):
            for date in list(rrule.rrule(rrule.WEEKLY, wkst=rrule.MO, byweekday=[jours_rrule[evenement_modele.jour]], dtstart=date_debut, until=date_fin)):
                date = date.date()

                # Validation des fériés
                if not modele.inclure_feries and utils_dates.EstFerie(date, liste_feries):
                    continue

                # Validation des périodes de vacances ou scolaires
                est_vacances = utils_dates.EstEnVacances(date=date, liste_vacances=liste_vacances)
                if evenement_modele.periode == "SCOLAIRES" and est_vacances: continue
                if evenement_modele.periode == "VACANCES" and not est_vacances: continue

                # Mémorisation de l'évènement à créer
                evenement = EvenementCollaborateur(collaborateur_id=idcollaborateur, type_evenement=evenement_modele.type_evenement,
                                                   date_debut=datetime.datetime.combine(date, evenement_modele.heure_debut),
                                                   date_fin=datetime.datetime.combine(date, evenement_modele.heure_fin),
                                                   titre=evenement_modele.titre)

                liste_evenements.append(evenement)

    # S'il n'y a aucun évènement à générer
    if not liste_evenements:
        return {"resultat": "erreur", "message_erreur": "Il n'existe aucun évènement à générer avec ces paramètres"}

    # Recherche les conflits éventuels
    evenements_valides = []
    evenements_refus = []

    evenements_existants = EvenementCollaborateur.objects.filter(collaborateur_id=idcollaborateur, date_debut__date__lte=date_fin, date_fin__date__gte=date_debut)
    contrats = ContratCollaborateur.objects.filter(collaborateur_id=idcollaborateur)

    for evenement_temp in liste_evenements:
        valide = True

        # Recherche des conflits dans les évènements existants
        for evenement in evenements_existants:
            if evenement_temp.date_debut <= evenement.date_fin and evenement_temp.date_fin >= evenement.date_debut:
                valide = False
                continue

        # Recherche des conflits dans les évènements à générer
        if valide:
            for evenement in evenements_valides:
                if evenement_temp.date_debut <= evenement.date_fin and evenement_temp.date_fin >= evenement.date_debut:
                    valide = False
                    continue

        # Recherche si la date est bien comprise dans un contrat
        if valide:
            if not Is_evenement_in_contrat(evenement=evenement_temp, contrats=contrats):
                valide = False

        # Mémorisation de l'évènement
        if valide:
            evenements_valides.append(evenement_temp)
        else:
            evenements_refus.append(evenement_temp)

    # Enregistrement dans la base
    EvenementCollaborateur.objects.bulk_create(evenements_valides)

    return {"resultat": "ok", "evenements_valides": evenements_valides, "evenements_refus": evenements_refus}
