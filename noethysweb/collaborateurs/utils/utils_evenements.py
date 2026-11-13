# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from core.models import EvenementCollaborateur, ContratCollaborateur


def Is_evenement_in_contrat(evenement=None, contrats=[]):
    """ Vérifie si un évènement est bien compris dans un contrat """
    for contrat in contrats:
        if not contrat.date_fin and evenement.date_debut.date() >= contrat.date_debut:
            return True
        if contrat.date_fin and evenement.date_debut.date() >= contrat.date_debut and evenement.date_fin.date() <= contrat.date_fin:
            return True
    return False


def Generation_evenements(idcollaborateur=None, modeles=[], date_debut=None, date_fin=None, departs={}, generateur=None, modeles_autorises=None):
    """ Application de modèles de planning à un collaborateur """
    from collaborateurs.utils.utils_modeles_planning import Generateur
    if not generateur:
        dates = [date_debut + datetime.timedelta(days=n) for n in range((date_fin - date_debut).days + 1)]
        generateur = Generateur(modeles=modeles, dates=dates, departs=departs)

    # Recherche des évènements à créer
    liste_evenements = []
    for date, ligne in generateur.Get_lignes_par_date():
        if modeles_autorises is not None and ligne.modele_id not in modeles_autorises:
            continue
        date_fin_evenement = datetime.datetime.combine(date, ligne.heure_fin)
        if ligne.heure_fin <= ligne.heure_debut:
            date_fin_evenement += datetime.timedelta(days=1)
        liste_evenements.append(EvenementCollaborateur(collaborateur_id=idcollaborateur, type_evenement=ligne.type_evenement,
                                                       date_debut=datetime.datetime.combine(date, ligne.heure_debut), date_fin=date_fin_evenement,
                                                       titre=ligne.titre, affectation_id=ligne.affectation_id))

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
