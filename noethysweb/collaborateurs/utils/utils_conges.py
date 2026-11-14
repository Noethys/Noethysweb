# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Congés et absences des collaborateurs : compteurs, demandes, validation.
    Les jours posés sont calculés à partir des évènements du planning de la catégorie liée au type de congé :
    les absences saisies directement dans le planning sont donc décomptées comme celles issues d'une demande validée. """

import datetime, decimal, json
from django.db import transaction
from django.db.models import Q, Sum
from core.models import Collaborateur, ContratCollaborateur, EvenementCollaborateur, TypeEvenementCollaborateur, Ferie, \
                        TypeCongeCollaborateur, DroitCongeCollaborateur, DemandeAbsenceCollaborateur
from core.utils import utils_dates, utils_historique
from collaborateurs.utils import utils_planning

PERMISSIONS = ("core.demandes_absences_collaborateurs", "core.compteurs_conges_collaborateurs")
JOURNEE_DEFAUT = {"journee_debut": "09:00", "journee_fin": "17:00", "matin_debut": "08:30", "matin_fin": "12:00", "am_debut": "13:30", "am_fin": "17:00"}
MINUTES_JOUR_DEFAUT = 420       # Durée de référence d'une journée sans contrat (7 h)
SEUIL_JOURNEE = 0.75            # Part de la journée de référence au-delà de laquelle une absence compte pour une journée entière
FORMAT_DATETIME = utils_planning.FORMAT_DATETIME


class Erreur(Exception):
    pass


def Peut_acceder(user=None):
    return user.is_superuser or any(user.has_perm(permission) for permission in PERMISSIONS)


def Peut_traiter(user=None, idcollaborateur=None):
    """ Peut valider les demandes et attribuer des droits : mêmes règles que la modification du planning (superviseurs des groupes) """
    return idcollaborateur in utils_planning.Get_ids_modifiables(user)


# ------------------------------------------------- Périodes et formats -------------------------------------------------

def Periode(type_conge=None, annee=None):
    debut = datetime.date(annee, type_conge.mois_debut, 1)
    fin = datetime.date(annee + 1, type_conge.mois_debut, 1) - datetime.timedelta(days=1)
    return {"annee": annee, "debut": debut, "fin": fin, "libelle": str(annee) if type_conge.mois_debut == 1 else "%d-%d" % (annee, annee + 1)}


def Annee_de(type_conge=None, date=None):
    return date.year if date.month >= type_conge.mois_debut else date.year - 1


def Format_valeur(valeur=0, unite="JOURS"):
    valeur = float(valeur or 0)
    if unite == "HEURES":
        signe = "-" if valeur < 0 else ""
        minutes = int(round(abs(valeur) * 60))
        return "%s%dh%02d" % (signe, minutes // 60, minutes % 60)
    texte = ("%.2f" % valeur).rstrip("0").rstrip(".").replace(".", ",")
    return "%s j" % (texte if texte not in ("-0", "") else "0")


def Decimal(valeur=0):
    return decimal.Decimal(str(round(valeur, 2))).quantize(decimal.Decimal("0.01"))


def Heure(texte=""):
    return datetime.datetime.strptime(texte, "%H:%M").time()


def Get_journee(user=None):
    """ Horaires de la journée type (préférences du planning individuel de l'utilisateur) """
    try:
        from collaborateurs.views.planning_individuel import Get_preferences
        preferences = Get_preferences(user)
    except Exception:
        preferences = {}
    return {nom: Heure(preferences.get(nom) or defaut) for nom, defaut in JOURNEE_DEFAUT.items()}


def Est_ouvre(date=None, liste_feries=[]):
    return date.weekday() < 5 and not utils_dates.EstFerie(date, liste_feries)


def Texte_periode_demande(demande=None):
    if demande.heure_debut and demande.heure_fin:
        return "%s de %s à %s" % (demande.date_debut.strftime("%d/%m/%Y"), demande.heure_debut.strftime("%Hh%M"), demande.heure_fin.strftime("%Hh%M"))
    if demande.date_debut == demande.date_fin:
        return demande.date_debut.strftime("%d/%m/%Y") + (" (après-midi)" if demande.debut_apres_midi else (" (matin)" if demande.fin_matin else ""))
    return "du %s%s au %s%s" % (demande.date_debut.strftime("%d/%m/%Y"), " (après-midi)" if demande.debut_apres_midi else "",
                                demande.date_fin.strftime("%d/%m/%Y"), " (matin)" if demande.fin_matin else "")


# ------------------------------------------------- Calcul d'une demande -------------------------------------------------

def Calculer_demande(demande=None, journee=None, liste_feries=None):
    """ Renvoie la durée décomptée et les créneaux d'absence d'une demande (non enregistrée ou enregistrée) """
    journee = journee or Get_journee()
    liste_feries = list(Ferie.objects.all()) if liste_feries is None else liste_feries
    if not demande.date_debut or not demande.date_fin:
        raise Erreur("Saisissez les dates de début et de fin")
    if demande.date_fin < demande.date_debut:
        raise Erreur("La date de fin doit être postérieure à la date de début")
    if (demande.date_fin - demande.date_debut).days > 366:
        raise Erreur("Une demande ne peut pas dépasser un an")
    unite = demande.type_conge.unite
    creneaux, quantite = [], 0.0
    minutes_journee = Minutes_creneau(journee["journee_debut"], journee["journee_fin"])

    if demande.heure_debut or demande.heure_fin:
        # Absence sur une plage horaire d'une seule journée
        if not (demande.heure_debut and demande.heure_fin):
            raise Erreur("Saisissez l'heure de début et l'heure de fin")
        if demande.date_debut != demande.date_fin:
            raise Erreur("Une absence sur une plage horaire doit tenir sur une seule journée")
        if demande.heure_fin <= demande.heure_debut:
            raise Erreur("L'heure de fin doit être postérieure à l'heure de début")
        if not Est_ouvre(demande.date_debut, liste_feries):
            raise Erreur("Le %s n'est pas un jour ouvré" % demande.date_debut.strftime("%d/%m/%Y"))
        debut = datetime.datetime.combine(demande.date_debut, demande.heure_debut)
        fin = datetime.datetime.combine(demande.date_debut, demande.heure_fin)
        minutes = (fin - debut).total_seconds() / 60
        creneaux.append({"debut": debut, "fin": fin, "journee": False})
        quantite = minutes / 60 if unite == "HEURES" else (1 if minutes >= SEUIL_JOURNEE * minutes_journee else 0.5)
    else:
        if demande.date_debut == demande.date_fin and demande.debut_apres_midi and demande.fin_matin:
            raise Erreur("Une absence d'une seule journée ne peut pas commencer l'après-midi et finir le matin")
        date = demande.date_debut
        while date <= demande.date_fin:
            if Est_ouvre(date, liste_feries):
                if date == demande.date_debut and demande.debut_apres_midi:
                    plage, valeur, journee_entiere = ("am_debut", "am_fin"), 0.5, False
                elif date == demande.date_fin and demande.fin_matin:
                    plage, valeur, journee_entiere = ("matin_debut", "matin_fin"), 0.5, False
                else:
                    plage, valeur, journee_entiere = ("journee_debut", "journee_fin"), 1, True
                debut = datetime.datetime.combine(date, journee[plage[0]])
                fin = datetime.datetime.combine(date, journee[plage[1]])
                creneaux.append({"debut": debut, "fin": fin, "journee": journee_entiere})
                quantite += (fin - debut).total_seconds() / 3600 if unite == "HEURES" else valeur
            date += datetime.timedelta(days=1)
        if not creneaux:
            raise Erreur("La période ne contient aucun jour ouvré")
    return {"quantite": Decimal(quantite), "creneaux": creneaux}


def Minutes_creneau(debut=None, fin=None):
    return (datetime.datetime.combine(datetime.date.today(), fin) - datetime.datetime.combine(datetime.date.today(), debut)).total_seconds() / 60


# ------------------------------------------------- Compteurs -------------------------------------------------

def Minutes_reference(contrats=[], date=None):
    """ Durée d'une journée de travail selon le contrat en cours (volume hebdomadaire / 5) """
    for contrat in contrats:
        if contrat.date_debut <= date and (not contrat.date_fin or date <= contrat.date_fin) and contrat.heures_hebdo:
            return float(contrat.heures_hebdo) / 5 * 60
    return MINUTES_JOUR_DEFAUT


def Calculer_poses(type_conge=None, collaborateurs=[], periode=None, liste_feries=[]):
    """ Jours ou heures posés par collaborateur : évènements du planning de la catégorie du type de congé sur la période """
    debut = datetime.datetime.combine(periode["debut"], datetime.time(0))
    fin = datetime.datetime.combine(periode["fin"] + datetime.timedelta(days=1), datetime.time(0))
    minutes_par_jour = {}
    for evenement in EvenementCollaborateur.objects.filter(type_evenement_id=type_conge.categorie_id, collaborateur_id__in=collaborateurs, date_debut__lt=fin, date_fin__gt=debut):
        date = max(evenement.date_debut, debut).date()
        while datetime.datetime.combine(date, datetime.time(0)) < min(evenement.date_fin, fin):
            jour_debut = datetime.datetime.combine(date, datetime.time(0))
            minutes = (min(evenement.date_fin, jour_debut + datetime.timedelta(days=1)) - max(evenement.date_debut, jour_debut)).total_seconds() / 60
            if minutes > 0:
                cle = (evenement.collaborateur_id, date)
                minutes_par_jour[cle] = minutes_par_jour.get(cle, 0) + minutes
            date += datetime.timedelta(days=1)

    contrats = {}
    if type_conge.unite == "JOURS":
        for contrat in ContratCollaborateur.objects.filter(collaborateur_id__in=collaborateurs):
            contrats.setdefault(contrat.collaborateur_id, []).append(contrat)
    poses = {}
    for (idcollaborateur, date), minutes in minutes_par_jour.items():
        if type_conge.unite == "HEURES":
            valeur = minutes / 60
        else:
            if not Est_ouvre(date, liste_feries):
                continue
            valeur = 1 if minutes >= SEUIL_JOURNEE * Minutes_reference(contrats.get(idcollaborateur, []), date) else 0.5
        poses[idcollaborateur] = poses.get(idcollaborateur, 0) + valeur
    return poses


def Get_compteurs(collaborateurs=[], types=None, date_reference=None, annee=None):
    """ Compteurs par collaborateur et par type : {(idcollaborateur, idtype): {...}}.
        La période est celle qui contient date_reference (aujourd'hui par défaut), ou celle qui commence l'année indiquée. """
    collaborateurs = list(collaborateurs)
    types = list(types) if types is not None else list(TypeCongeCollaborateur.objects.select_related("categorie").order_by("ordre", "nom"))
    date_reference = date_reference or datetime.date.today()
    liste_feries = list(Ferie.objects.all())
    resultats = {}
    for type_conge in types:
        periode = Periode(type_conge, annee if annee else Annee_de(type_conge, date_reference))
        droits = {ligne["collaborateur_id"]: float(ligne["total"]) for ligne in DroitCongeCollaborateur.objects.filter(
            type_conge=type_conge, annee=periode["annee"], collaborateur_id__in=collaborateurs).values("collaborateur_id").annotate(total=Sum("valeur"))}
        attente = {ligne["collaborateur_id"]: float(ligne["total"]) for ligne in DemandeAbsenceCollaborateur.objects.filter(
            type_conge=type_conge, etat="ATTENTE", collaborateur_id__in=collaborateurs, date_debut__gte=periode["debut"], date_debut__lte=periode["fin"]).values("collaborateur_id").annotate(total=Sum("quantite"))}
        poses = Calculer_poses(type_conge, collaborateurs, periode, liste_feries)
        for idcollaborateur in collaborateurs:
            valeurs = {"droits": droits.get(idcollaborateur, 0), "poses": poses.get(idcollaborateur, 0), "attente": attente.get(idcollaborateur, 0)}
            valeurs["solde"] = valeurs["droits"] - valeurs["poses"]
            valeurs["previsionnel"] = valeurs["solde"] - valeurs["attente"]
            textes = {"%s_txt" % cle: Format_valeur(valeur, type_conge.unite) for cle, valeur in valeurs.items()}
            resultats[(idcollaborateur, type_conge.pk)] = dict(valeurs, **textes, type=type_conge.pk, nom=type_conge.nom, unite=type_conge.unite,
                                                                periode=periode["libelle"], annee=periode["annee"],
                                                                periode_debut=str(periode["debut"]), periode_fin=str(periode["fin"]))
    return resultats


# ------------------------------------------------- Traitement des demandes -------------------------------------------------

def Evenements_travail(idcollaborateur=None, creneaux=[]):
    """ Evènements de travail (temps comptabilisé) retirés par la validation : journées entières pour les jours complets, créneau sinon """
    conditions = Q()
    for creneau in creneaux:
        if creneau["journee"]:
            jour = datetime.datetime.combine(creneau["debut"].date(), datetime.time(0))
            conditions |= Q(date_debut__lt=jour + datetime.timedelta(days=1), date_fin__gt=jour)
        else:
            conditions |= Q(date_debut__lt=creneau["fin"], date_fin__gt=creneau["debut"])
    if not creneaux:
        return EvenementCollaborateur.objects.none()
    return EvenementCollaborateur.objects.filter(conditions, collaborateur_id=idcollaborateur, type_evenement__type="ADDITION").select_related("type_evenement").order_by("date_debut")


def Absences_equipe(demande=None):
    """ Absences des autres collaborateurs des mêmes groupes sur la période de la demande """
    groupes = list(demande.collaborateur.groupes.values_list("pk", flat=True))
    if not groupes:
        return []
    collegues = Collaborateur.objects.filter(groupes__in=groupes).exclude(pk=demande.collaborateur_id).distinct()
    debut = datetime.datetime.combine(demande.date_debut, datetime.time(0))
    fin = datetime.datetime.combine(demande.date_fin + datetime.timedelta(days=1), datetime.time(0))
    categories_absence = set(TypeCongeCollaborateur.objects.values_list("categorie_id", flat=True)) | set(TypeEvenementCollaborateur.objects.filter(type="SOUSTRACTION").values_list("pk", flat=True))
    absences = {}
    for evenement in EvenementCollaborateur.objects.filter(collaborateur__in=collegues, type_evenement_id__in=categories_absence, date_debut__lt=fin, date_fin__gt=debut).select_related("collaborateur"):
        dates = absences.setdefault(evenement.collaborateur, set())
        date = evenement.date_debut.date()
        while date <= (evenement.date_fin - datetime.timedelta(minutes=1)).date():
            if demande.date_debut <= date <= demande.date_fin:
                dates.add(date)
            date += datetime.timedelta(days=1)
    resultats = []
    for collaborateur, dates in sorted(absences.items(), key=lambda item: item[0].Get_nom()):
        if dates:
            resultats.append({"nom": collaborateur.Get_nom(), "texte": Texte_dates(sorted(dates)), "attente": False})
    for autre in DemandeAbsenceCollaborateur.objects.filter(collaborateur__in=collegues, etat="ATTENTE", date_debut__lte=demande.date_fin, date_fin__gte=demande.date_debut).select_related("collaborateur"):
        resultats.append({"nom": autre.collaborateur.Get_nom(), "texte": Texte_periode_demande(autre) + " (demande en attente)", "attente": True})
    return resultats


def Texte_dates(dates=[]):
    """ 22/12, 23/12 et 28/12 -> "22/12 → 23/12, 28/12" """
    plages = []
    for date in dates:
        if plages and date - plages[-1][1] == datetime.timedelta(days=1):
            plages[-1][1] = date
        else:
            plages.append([date, date])
    return ", ".join(debut.strftime("%d/%m") if debut == fin else "%s → %s" % (debut.strftime("%d/%m"), fin.strftime("%d/%m")) for debut, fin in plages)


def Apercu(demande=None, user=None, journee=None):
    """ Impacts de la validation d'une demande, affichés avant la décision """
    calcul = Calculer_demande(demande, journee or Get_journee(user))
    type_conge = demande.type_conge
    compteur = Get_compteurs([demande.collaborateur_id], [type_conge], annee=Annee_de(type_conge, demande.date_debut))[(demande.collaborateur_id, type_conge.pk)]
    deja_compte = float(demande.quantite) if demande.pk and demande.etat == "ATTENTE" else 0
    solde_apres = compteur["solde"] - float(calcul["quantite"])
    travail = list(Evenements_travail(demande.collaborateur_id, calcul["creneaux"]))
    ids_travail = {evenement.pk for evenement in travail}

    # Evènements existants incompatibles avec l'absence (hors travail retiré)
    conflits = []
    for creneau in calcul["creneaux"]:
        for evenement in EvenementCollaborateur.objects.filter(collaborateur_id=demande.collaborateur_id, date_debut__lt=creneau["fin"], date_fin__gt=creneau["debut"]).exclude(pk__in=ids_travail).select_related("type_evenement"):
            if not (evenement.type_evenement.chevauchement_possible or type_conge.categorie.chevauchement_possible):
                conflits.append("%s le %s de %s à %s" % (evenement.type_evenement.nom, evenement.date_debut.strftime("%d/%m/%Y"), evenement.date_debut.strftime("%Hh%M"), evenement.date_fin.strftime("%Hh%M")))

    erreurs = []
    if conflits:
        erreurs.append("Le planning contient déjà des évènements sur ces créneaux : %s" % ", ".join(sorted(set(conflits))))
    if not type_conge.solde_negatif and solde_apres < -0.001:
        erreurs.append("Le solde serait négatif (%s) et ce type de congé ne l'autorise pas" % Format_valeur(solde_apres, type_conge.unite))

    textes_creneaux = []
    for creneau in calcul["creneaux"]:
        textes_creneaux.append("%s %s-%s" % (creneau["debut"].strftime("%d/%m"), creneau["debut"].strftime("%Hh%M"), creneau["fin"].strftime("%Hh%M")))
    return {
        "quantite": float(calcul["quantite"]), "quantite_txt": Format_valeur(calcul["quantite"], type_conge.unite),
        "periode": compteur["periode"], "solde_txt": compteur["solde_txt"], "solde_apres": solde_apres, "solde_apres_txt": Format_valeur(solde_apres, type_conge.unite),
        "attente_autres_txt": Format_valeur(compteur["attente"] - deja_compte, type_conge.unite) if compteur["attente"] - deja_compte > 0.001 else "",
        "creneaux": textes_creneaux, "categorie": type_conge.categorie.nom,
        "travail": ["%s le %s de %s à %s" % (evenement.type_evenement.nom, evenement.date_debut.strftime("%d/%m"), evenement.date_debut.strftime("%Hh%M"), evenement.date_fin.strftime("%Hh%M")) for evenement in travail],
        "equipe": Absences_equipe(demande), "erreurs": erreurs,
    }


def Serialiser_evenement(evenement=None):
    return {"c": evenement.collaborateur_id, "cat": evenement.type_evenement_id, "aff": evenement.affectation_id, "t": evenement.titre or "",
            "d": evenement.date_debut.strftime(FORMAT_DATETIME), "f": evenement.date_fin.strftime(FORMAT_DATETIME),
            "rd": evenement.realise_debut.strftime(FORMAT_DATETIME) if evenement.realise_debut else None,
            "rf": evenement.realise_fin.strftime(FORMAT_DATETIME) if evenement.realise_fin else None}


def Historique(demande=None, user=None, action=""):
    utils_historique.Ajouter(titre=action, detail="%s : %s, %s" % (demande.type_conge.nom, Texte_periode_demande(demande), Format_valeur(demande.quantite, demande.type_conge.unite)),
                             utilisateur=user, collaborateur=demande.collaborateur_id, objet="Demande d'absence", idobjet=demande.pk, classe="DemandeAbsenceCollaborateur")


def Valider(demande=None, user=None, commentaire=""):
    with transaction.atomic():
        demande = DemandeAbsenceCollaborateur.objects.select_for_update().select_related("type_conge__categorie", "collaborateur").get(pk=demande.pk)
        if demande.etat != "ATTENTE":
            raise Erreur("Cette demande a déjà été traitée")
        apercu = Apercu(demande, user)
        if apercu["erreurs"]:
            raise Erreur(" ; ".join(apercu["erreurs"]))
        calcul = Calculer_demande(demande, Get_journee(user))

        # Retrait du travail prévu sur les créneaux d'absence (mémorisé pour une éventuelle restauration)
        travail = list(Evenements_travail(demande.collaborateur_id, calcul["creneaux"]))
        demande.evenements_retires = json.dumps([Serialiser_evenement(evenement) for evenement in travail]) if travail else None
        for evenement in travail:
            evenement.delete()

        # Création des absences
        titre = demande.type_conge.nom if demande.type_conge.nom.lower() != demande.type_conge.categorie.nom.lower() else ""
        crees = [EvenementCollaborateur.objects.create(collaborateur=demande.collaborateur, type_evenement=demande.type_conge.categorie, titre=titre,
                                                       date_debut=creneau["debut"], date_fin=creneau["fin"]) for creneau in calcul["creneaux"]]
        demande.evenements.set(crees)
        demande.quantite = calcul["quantite"]
        demande.etat = "VALIDEE"
        demande.decideur = user
        demande.commentaire = commentaire or None
        demande.date_decision = datetime.datetime.now()
        demande.save()
        Historique(demande, user, "Validation d'une demande d'absence")
    return {"crees": len(crees), "retires": len(travail)}


def Refuser(demande=None, user=None, commentaire=""):
    with transaction.atomic():
        demande = DemandeAbsenceCollaborateur.objects.select_for_update().get(pk=demande.pk)
        if demande.etat != "ATTENTE":
            raise Erreur("Cette demande a déjà été traitée")
        demande.etat = "REFUSEE"
        demande.decideur = user
        demande.commentaire = commentaire or None
        demande.date_decision = datetime.datetime.now()
        demande.save()
        Historique(demande, user, "Refus d'une demande d'absence")


def Annuler(demande=None, user=None, restaurer=True, commentaire=""):
    """ Annule une demande. Pour une demande validée : supprime les absences créées et restaure éventuellement le travail retiré """
    restaures, ignores = 0, 0
    with transaction.atomic():
        demande = DemandeAbsenceCollaborateur.objects.select_for_update().get(pk=demande.pk)
        if demande.etat not in ("ATTENTE", "VALIDEE"):
            raise Erreur("Cette demande est déjà refusée ou annulée")
        if demande.etat == "VALIDEE":
            demande.evenements.all().delete()
            if restaurer and demande.evenements_retires:
                categories = {categorie.pk: categorie for categorie in TypeEvenementCollaborateur.objects.all()}
                for donnees in json.loads(demande.evenements_retires):
                    debut, fin = utils_planning.Parse_datetime(donnees["d"]), utils_planning.Parse_datetime(donnees["f"])
                    categorie = categories.get(donnees["cat"])
                    if not categorie:
                        ignores += 1
                        continue
                    occupes = EvenementCollaborateur.objects.filter(collaborateur_id=donnees["c"], date_debut__lt=fin, date_fin__gt=debut).select_related("type_evenement")
                    if any(not (autre.type_evenement.chevauchement_possible or categorie.chevauchement_possible) for autre in occupes):
                        ignores += 1
                        continue
                    EvenementCollaborateur.objects.create(collaborateur_id=donnees["c"], type_evenement=categorie, affectation_id=donnees.get("aff"), titre=donnees.get("t") or None,
                                                          date_debut=debut, date_fin=fin, realise_debut=utils_planning.Parse_datetime(donnees.get("rd")),
                                                          realise_fin=utils_planning.Parse_datetime(donnees.get("rf")))
                    restaures += 1
            demande.evenements_retires = None
        demande.etat = "ANNULEE"
        if commentaire:
            demande.commentaire = commentaire
        demande.save()
        Historique(demande, user, "Annulation d'une demande d'absence")
    return {"restaures": restaures, "ignores": ignores}


def Serialiser_demande(demande=None, user=None, ids_modifiables=None):
    ids_modifiables = ids_modifiables if ids_modifiables is not None else utils_planning.Get_ids_modifiables(user)
    return {
        "id": demande.pk, "c": demande.collaborateur_id, "collaborateur": demande.collaborateur.Get_nom(), "type": demande.type_conge_id, "type_nom": demande.type_conge.nom,
        "unite": demande.type_conge.unite, "couleur": demande.type_conge.categorie.couleur,
        "date_debut": str(demande.date_debut), "debut_apres_midi": demande.debut_apres_midi, "date_fin": str(demande.date_fin), "fin_matin": demande.fin_matin,
        "heure_debut": demande.heure_debut.strftime("%H:%M") if demande.heure_debut else "", "heure_fin": demande.heure_fin.strftime("%H:%M") if demande.heure_fin else "",
        "periode_txt": Texte_periode_demande(demande), "quantite_txt": Format_valeur(demande.quantite, demande.type_conge.unite),
        "etat": demande.etat, "etat_txt": demande.get_etat_display(), "motif": demande.motif or "", "commentaire": demande.commentaire or "",
        "date_demande": demande.date_demande.strftime("%d/%m/%Y"), "auteur": (demande.auteur.get_full_name() or demande.auteur.username) if demande.auteur else "",
        "decideur": (demande.decideur.get_full_name() or demande.decideur.username) if demande.decideur else "",
        "date_decision": demande.date_decision.strftime("%d/%m/%Y") if demande.date_decision else "",
        "traitable": demande.collaborateur_id in ids_modifiables, "retires": bool(demande.evenements_retires),
    }
