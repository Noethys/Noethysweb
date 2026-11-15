# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Données des widgets collaborateurs de la page d'accueil """

import datetime, math
from django.db.models import Q, Exists, OuterRef
from core.models import Collaborateur, ContratCollaborateur, DemandeAbsenceCollaborateur, EvenementCollaborateur
from collaborateurs.utils import utils_planning, utils_conges, utils_absences, utils_pieces_manquantes
from collaborateurs.utils.utils_affectations import Arbre

NBRE_LIGNES_MAX = 8
DELAI_URGENCE_DEMANDE = 7           # Jours avant le début d'une demande à partir duquel elle est signalée comme urgente
DELAI_EXPIRATION_PIECES = 30        # Jours avant l'expiration d'une pièce à partir duquel elle est signalée
SEUIL_ALERTE_ENCADREMENT = 0.85     # Part du taux maximal à partir de laquelle l'encadrement passe en orange
ORDRE_ETATS_PIECES = {"ABSENTE": 0, "EXPIREE": 1, "REFUSEE": 2, "BIENTOT": 3, "ATTENTE": 4}
LABELS_ETATS_PIECES = {"ABSENTE": "Manquante", "EXPIREE": "Expirée", "REFUSEE": "Refusée", "BIENTOT": "Expire bientôt", "ATTENTE": "A vérifier"}
CLASSES_ETATS_PIECES = {"ABSENTE": "danger", "EXPIREE": "danger", "REFUSEE": "warning", "BIENTOT": "warning", "ATTENTE": "secondary"}


# ------------------------------------------------- Outils -------------------------------------------------

def Ids_visibles(user=None):
    """ Collaborateurs visibles par l'utilisateur (superviseurs des groupes ou groupes sans superviseur) """
    if user.is_superuser:
        return set(Collaborateur.objects.values_list("pk", flat=True))
    conditions = Q(groupes__superviseurs=user) | Q(groupes__superviseurs__isnull=True)
    return set(Collaborateur.objects.filter(conditions).values_list("pk", flat=True).distinct())


def Nom_court(collaborateur=None):
    """ Prénom et initiale du nom (ex : Claire L.) """
    if not collaborateur.prenom:
        return collaborateur.nom
    return "%s %s." % (collaborateur.prenom, collaborateur.nom[:1].upper()) if collaborateur.nom else collaborateur.prenom


def Initiales(collaborateur=None):
    return ((collaborateur.prenom or "")[:1] + (collaborateur.nom or "")[:1]).upper()


def Lire_date(texte=None):
    """ Date AAAA-MM-JJ envoyée par le widget, aujourd'hui par défaut ou si invalide """
    try:
        return datetime.datetime.strptime(texte, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return datetime.date.today()


def Selecteur_date(context={}, code_widget="", id_champ=""):
    """ Calendrier Noethysweb (vacances et fériés) encadré de flèches veille / lendemain, positionné sur aujourd'hui.
        Les scripts du calendrier ne sont inclus que par le premier widget de la page qui l'utilise. """
    from core.widgets import DatePickerWidget
    widget = DatePickerWidget(attrs={"fleches_encadrantes": True, "taille_groupe": "sm"})
    context.setdefault("collaborateurs_datepicker_media", {"code": code_widget, "html": str(widget.media)})
    return widget.render("date_%s" % code_widget, datetime.date.today(), attrs={"id": id_champ, "class": "form-control", "aria_label": "Date affichée"})


def Minutes_dans_jour(debut=None, fin=None, date=None):
    """ Minutes de [debut, fin] comprises dans la journée """
    if not debut or not fin:
        return 0
    jour = datetime.datetime.combine(date, datetime.time(0))
    return max(0, (min(fin, jour + datetime.timedelta(days=1)) - max(debut, jour)).total_seconds() / 60)


# ------------------------------------------------- Demandes d'absence -------------------------------------------------

def Get_demandes_absences(user=None):
    """ Demandes d'absence en attente que l'utilisateur peut traiter, les plus proches en premier """
    aujourdhui = datetime.date.today()
    demandes = DemandeAbsenceCollaborateur.objects.select_related("collaborateur", "type_conge").filter(
        etat="ATTENTE", collaborateur_id__in=utils_planning.Get_ids_modifiables(user)).order_by("date_debut", "collaborateur__nom")
    lignes = []
    for demande in demandes:
        jours = (demande.date_debut - aujourdhui).days
        if jours < 0:
            delai = "Commencée"
        elif jours == 0:
            delai = "Aujourd'hui"
        elif jours == 1:
            delai = "Demain"
        else:
            delai = "Dans %d j" % jours
        lignes.append({
            "demande": demande, "initiales": Initiales(demande.collaborateur), "nom": demande.collaborateur.Get_nom(),
            "type_conge": demande.type_conge.nom, "periode": utils_conges.Texte_periode_demande(demande),
            "duree": utils_conges.Format_valeur(demande.quantite, demande.type_conge.unite),
            "delai": delai, "urgent": jours <= DELAI_URGENCE_DEMANDE,
        })
    return {"lignes": lignes[:NBRE_LIGNES_MAX], "total": len(lignes), "nbre_urgents": len([ligne for ligne in lignes if ligne["urgent"]])}


# ------------------------------------------------- Heures déclarées -------------------------------------------------

def Get_heures_declarees(user=None):
    """ Déclarations d'heures en attente de validation, les plus gros écarts en premier """
    from collaborateurs.views.heures_declarees import Ecart, Texte_ecart
    lignes = []
    for evenement in EvenementCollaborateur.objects.select_related("collaborateur").filter(
            declare_etat="ATTENTE", declare_debut__isnull=False, declare_fin__isnull=False,
            collaborateur_id__in=utils_planning.Get_ids_modifiables(user)).order_by("date_debut"):
        ecart = Ecart(evenement)
        lignes.append({"evenement": evenement, "nom": evenement.collaborateur.Get_nom(),
                       "ecart": ecart, "texte_ecart": Texte_ecart(ecart),
                       "classe": "danger" if abs(ecart) >= 60 else ("warning" if abs(ecart) >= 15 else "secondary")})
    lignes.sort(key=lambda ligne: -abs(ligne["ecart"]))
    return {"lignes": lignes[:NBRE_LIGNES_MAX], "total": len(lignes)}


# ------------------------------------------------- Pièces manquantes -------------------------------------------------

def Get_pieces_manquantes(user=None):
    """ Pièces manquantes, refusées, expirées, bientôt expirées ou à vérifier des collaborateurs en poste ou à venir """
    aujourdhui = datetime.date.today()
    contrats = ContratCollaborateur.objects.filter(Q(date_fin__isnull=True) | Q(date_fin__gte=aujourdhui), collaborateur=OuterRef("pk"))
    collaborateurs = list(Collaborateur.objects.filter(pk__in=Ids_visibles(user)).filter(Exists(contrats)).order_by("nom", "prenom"))
    dict_collaborateurs = {collaborateur.pk: collaborateur for collaborateur in collaborateurs}
    pieces = utils_pieces_manquantes.Get_liste_pieces_manquantes(collaborateurs=collaborateurs, date_reference=aujourdhui, delai_expiration=DELAI_EXPIRATION_PIECES)
    lignes = []
    for idcollaborateur, liste in pieces.items():
        collaborateur = dict_collaborateurs[idcollaborateur]
        for piece in liste:
            etat = piece["etat"]
            if etat not in ORDRE_ETATS_PIECES:
                continue
            label = LABELS_ETATS_PIECES[etat]
            if etat == "BIENTOT" and piece.get("date_fin"):
                label = "Expire le %s" % piece["date_fin"].strftime("%d/%m")
            lignes.append({"collaborateur": collaborateur, "nom": collaborateur.Get_nom(),
                           "piece": piece["type_piece"].nom, "etat": etat, "label": label, "classe": CLASSES_ETATS_PIECES[etat],
                           "date_fin": piece.get("date_fin") or datetime.date(2999, 1, 1)})
    lignes.sort(key=lambda ligne: (ORDRE_ETATS_PIECES[ligne["etat"]], ligne["date_fin"], ligne["nom"]))
    return {"lignes": lignes[:NBRE_LIGNES_MAX], "total": len(lignes), "nbre_collaborateurs": len({ligne["collaborateur"].pk for ligne in lignes})}


# ------------------------------------------------- Equipe du jour -------------------------------------------------

def Get_equipe_du_jour(user=None, date=None):
    """ Collaborateurs planifiés par affectation et absents à une date. Les absences sont affichées sans leur motif. """
    date = date or datetime.date.today()
    ids_visibles = Ids_visibles(user)
    categories_absence = utils_absences.Get_categories_absence()
    arbre = Arbre()
    ordre_affectations = {affectation.pk: index for index, (affectation, niveau) in enumerate(arbre.Parcourir())}

    presents, absents, minutes_total = {}, {}, 0
    plages = {}     # {(affectation ou None, idcollaborateur): [[début, fin], ...]}
    debut_jour = datetime.datetime.combine(date, datetime.time(0))
    fin_jour = debut_jour + datetime.timedelta(days=1)
    for evenement in utils_planning.Get_evenements(date, date, ids_visibles).select_related("collaborateur", "type_evenement"):
        minutes = Minutes_dans_jour(evenement.date_debut, evenement.date_fin, date)
        if not minutes:
            continue
        collaborateur = evenement.collaborateur
        if evenement.type_evenement_id in categories_absence:
            absents[collaborateur.pk] = collaborateur
            continue
        if not evenement.type_evenement or evenement.type_evenement.type != "ADDITION":
            continue
        presents[collaborateur.pk] = collaborateur
        minutes_total += minutes
        cle = evenement.affectation_id if evenement.affectation_id in arbre.affectations else None
        plages.setdefault((cle, collaborateur.pk), []).append([max(evenement.date_debut, debut_jour), min(evenement.date_fin, fin_jour)])

    # Créneaux : les évènements d'un collaborateur qui se chevauchent ou se suivent dans une même affectation forment un seul créneau.
    # Les collaborateurs ayant exactement le même créneau sont regroupés sur une ligne.
    creneaux = {}   # {affectation ou None: {(début, fin): [collaborateurs]}}
    for (cle, idcollaborateur), liste in plages.items():
        fusion = []
        for debut, fin in sorted(liste):
            if fusion and debut <= fusion[-1][1]:
                fusion[-1][1] = max(fusion[-1][1], fin)
            else:
                fusion.append([debut, fin])
        for debut, fin in fusion:
            creneaux.setdefault(cle, {}).setdefault((debut, fin), []).append(presents[idcollaborateur])

    def Heure(valeur):
        return "24:00" if valeur == fin_jour else valeur.strftime("%H:%M")

    lignes = []
    for cle, dict_creneaux in sorted(creneaux.items(), key=lambda item: ordre_affectations.get(item[0], 99999)):
        affectation = arbre.affectations.get(cle)
        liste_creneaux = []
        for (debut, fin), collaborateurs in sorted(dict_creneaux.items()):
            noms = [Nom_court(collaborateur) for collaborateur in sorted(collaborateurs, key=lambda c: (c.prenom or "", c.nom))]
            liste_creneaux.append({
                "horaires": "%s–%s" % (Heure(debut), Heure(fin)),
                "noms": ", ".join(noms[:4]) + (" +%d" % (len(noms) - 4) if len(noms) > 4 else ""),
                "noms_complets": ", ".join(noms), "nbre": len(noms),
            })
        lignes.append({
            "nom": affectation.nom if affectation else "Sans affectation",
            "chemin": arbre.Get_chemin(affectation.parent_id) if affectation and affectation.parent_id else "",
            "couleur": (affectation.couleur if affectation else None) or "#adb5bd",
            "creneaux": liste_creneaux,
        })

    return {
        "date": date, "lignes": lignes, "nbre_presents": len(presents), "nbre_absents": len(absents),
        "heures": utils_planning.Format_minutes(minutes_total),
        "absents": ", ".join(Nom_court(collaborateur) for collaborateur in sorted(absents.values(), key=lambda c: (c.nom, c.prenom or ""))),
    }


# ------------------------------------------------- Taux d'encadrement -------------------------------------------------

def Get_encadrement(date=None):
    """ Taux d'encadrement par affectation : pic des consommations réservées (réservations et présences) sur les unités de remplissage
        de l'affectation, rapporté au nombre de collaborateurs ayant du temps comptabilisé dans son sous-arbre (même calcul que le planning).
        Tous les collaborateurs sont comptés, quel que soit l'utilisateur : seuls des effectifs sont renvoyés. """
    date = date or datetime.date.today()
    remplissages = utils_planning.Get_remplissages(date, date)
    if not remplissages:
        return {"date": date, "lignes": []}
    arbre = Arbre()

    # Minutes comptabilisées par affectation et par collaborateur
    minutes = {}
    for evenement in utils_planning.Get_evenements(date, date).select_related("type_evenement").filter(affectation__isnull=False):
        if not evenement.type_evenement or evenement.type_evenement.type not in ("ADDITION", "SOUSTRACTION"):
            continue
        signe = 1 if evenement.type_evenement.type == "ADDITION" else -1
        cle = (evenement.affectation_id, evenement.collaborateur_id)
        minutes[cle] = minutes.get(cle, 0) + signe * Minutes_dans_jour(evenement.date_debut, evenement.date_fin, date)

    def Descendants(idaffectation):
        ids = {idaffectation}
        for enfant in arbre.enfants.get(idaffectation, []):
            ids |= Descendants(enfant.pk)
        return ids

    lignes = []
    for affectation, niveau in arbre.Parcourir():
        liste = remplissages.get("%s|%d" % (date, affectation.pk))
        seuil = arbre.Get_seuil_encadrement(affectation.pk)
        if not liste or not seuil or not (affectation.seuil_encadrement or affectation.activite_id):
            continue
        pic = max(item["p"] for item in liste)
        if not pic:
            continue
        sous_arbre = Descendants(affectation.pk)
        nbre_collaborateurs = len({idcollaborateur for (idaffectation, idcollaborateur), total in minutes.items() if idaffectation in sous_arbre and total > 0})
        taux = pic / nbre_collaborateurs if nbre_collaborateurs else None
        depasse = taux is None or taux > seuil
        alerte = not depasse and taux >= SEUIL_ALERTE_ENCADREMENT * seuil
        lignes.append({
            "nom": affectation.nom, "chemin": arbre.Get_chemin(affectation.parent_id) if affectation.parent_id else "",
            "pic": pic, "nbre_collaborateurs": nbre_collaborateurs, "seuil": seuil,
            "taux": int(round(taux)) if taux else None,
            "classe": "danger" if depasse else ("warning" if alerte else "success"),
            "pourcentage": 100 if taux is None else min(100, int(round(taux / seuil * 100))),
            "manque": max(1, math.ceil(pic / seuil) - nbre_collaborateurs) if depasse else 0,
        })
    lignes.sort(key=lambda ligne: {"danger": 0, "warning": 1, "success": 2}[ligne["classe"]])
    return {"date": date, "lignes": lignes, "nbre_depassements": len([ligne for ligne in lignes if ligne["classe"] == "danger"])}
