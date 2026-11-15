# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Eléments variables de paie d'un mois : heures travaillées, heures complémentaires et supplémentaires, majorations, absences.

    Règles de calcul (paramétrables en partie) :
    - Heures retenues : le réalisé lorsqu'il est saisi, sinon le planifié (ou toujours le planifié selon le paramètre).
    - Heures travaillées : évènements des catégories en temps comptabilisé, rattachés au jour où ils commencent.
    - Absences assimilées : absences des catégories comptées comme du temps de travail (congés, maladie...), ajoutées aux heures travaillées
      pour calculer l'écart avec les heures attendues, mais pas pour les heures complémentaires et supplémentaires (temps de travail effectif).
    - Heures complémentaires et supplémentaires : calculées par semaine civile (lundi-dimanche) pour les contrats en mode hebdomadaire,
      au-delà du volume hebdomadaire du contrat. Une semaine est rattachée au mois de son dimanche (ou de son lundi selon le paramètre).
      Temps plein (volume >= durée légale) : heures supplémentaires majorées de 25 % jusqu'à la 43e heure (durée légale + 8 h), 50 % au-delà.
      Temps partiel : heures complémentaires majorées de 10 % dans la limite de 10 % du volume du contrat, 25 % au-delà.
    - Contrats annualisés, en volume fixe ou au forfait jours : pas de calcul hebdomadaire (suivi par l'objectif annuel du planning individuel). """

import datetime
from core.models import ContratCollaborateur, TypeEvenementCollaborateur, TypeCongeCollaborateur, DemandeAbsenceCollaborateur, \
                        EvenementCollaborateur, Ferie
from core.utils import utils_dates
from collaborateurs.utils import utils_planning, utils_conges, utils_absences

HEURES_MAJOREES_25 = 8      # Nombre d'heures supplémentaires majorées à 25 % au-delà de la durée légale
PART_HC_10 = 0.10           # Part du volume du contrat des heures complémentaires majorées à 10 %


def Limites_mois(mois=None):
    """ Premier et dernier jour du mois (mois = date du premier jour) """
    suivant = datetime.date(mois.year + (mois.month == 12), mois.month % 12 + 1, 1)
    return mois, suivant - datetime.timedelta(days=1)


def Semaines_du_mois(date_debut=None, date_fin=None, rattachement="FIN"):
    """ Semaines (lundi, dimanche) rattachées au mois : celles dont le dimanche (FIN) ou le lundi (DEBUT) est dans le mois """
    semaines = []
    lundi = date_debut - datetime.timedelta(days=date_debut.weekday() + 7)
    while lundi <= date_fin:
        dimanche = lundi + datetime.timedelta(days=6)
        jour_reference = dimanche if rattachement == "FIN" else lundi
        if date_debut <= jour_reference <= date_fin:
            semaines.append((lundi, dimanche))
        lundi += datetime.timedelta(days=7)
    return semaines


def Duree_retenue(evenement=None, realise=True):
    """ Durée retenue d'un évènement en minutes et horaires correspondants """
    if realise and evenement.realise_debut and evenement.realise_fin:
        debut, fin = evenement.realise_debut, evenement.realise_fin
    else:
        debut, fin = evenement.date_debut, evenement.date_fin
    return (fin - debut).total_seconds() / 60, debut, fin


def Contrat_semaine(contrats=[], lundi=None, dimanche=None):
    """ Contrat de référence d'une semaine : celui en cours le dernier jour couvert de la semaine """
    date = dimanche
    while date >= lundi:
        contrat = utils_conges.Contrat_du_jour(contrats, date)
        if contrat:
            return contrat
        date -= datetime.timedelta(days=1)
    return None


def Calculer_semaine(minutes=0, contrats=[], lundi=None, dimanche=None, duree_legale=35):
    """ Heures complémentaires ou supplémentaires d'une semaine. Renvoie None si la semaine n'est pas concernée. """
    contrat = Contrat_semaine(contrats, lundi, dimanche)
    if not contrat or not contrat.heures_hebdo or (contrat.objectif_mode or "HEBDO") != "HEBDO":
        return None
    dates = [lundi + datetime.timedelta(days=n) for n in range(7)]
    couverte = all(utils_conges.Contrat_du_jour(contrats, date) for date in dates)
    heures_hebdo = float(contrat.heures_hebdo)
    # Semaine incomplète (début ou fin de contrat) : volume proratisé sur les jours couverts
    reference = heures_hebdo * 60 if couverte else utils_planning.Heures_attendues(contrats, dates, [])
    resultat = {"lundi": lundi, "dimanche": dimanche, "contrat": contrat, "reference": reference, "travaille": minutes, "depassement": max(0.0, minutes - reference),
                "temps_plein": heures_hebdo >= duree_legale, "hc10": 0.0, "hc25": 0.0, "hs25": 0.0, "hs50": 0.0, "alerte": ""}
    depassement = resultat["depassement"]
    if resultat["temps_plein"]:
        plafond_25 = max(0.0, (duree_legale + HEURES_MAJOREES_25) * 60 - max(reference, duree_legale * 60))
        resultat["hs25"] = min(depassement, plafond_25)
        resultat["hs50"] = depassement - resultat["hs25"]
    else:
        resultat["hc10"] = min(depassement, PART_HC_10 * reference)
        resultat["hc25"] = depassement - resultat["hc10"]
        if minutes >= duree_legale * 60:
            resultat["alerte"] = "Temps partiel : la durée légale est atteinte"
    return resultat


def Minutes_assimilees(evenements=[], categories={}, contrats=[]):
    """ Minutes d'absence comptées comme du temps de travail : durée planifiée (règle DUREE) ou durée forfaitaire d'une journée du contrat (règle FORFAIT,
        une demi-journée si l'absence dure moins de 4 heures dans la journée) """
    from collaborateurs.utils.utils_objectif import SEUIL_DEMI_JOURNEE
    total, forfaits = 0.0, {}
    for evenement in evenements:
        categorie = categories.get(evenement.type_evenement_id)
        if not categorie or categorie.temps_travail_objectif not in ("DUREE", "FORFAIT"):
            continue
        if categorie.temps_travail_objectif == "DUREE":
            total += (evenement.date_fin - evenement.date_debut).total_seconds() / 60
        else:
            jour = evenement.date_debut.date()
            forfaits[jour] = forfaits.get(jour, 0) + (evenement.date_fin - evenement.date_debut).total_seconds() / 60
    for jour, minutes in forfaits.items():
        reference = utils_conges.Minutes_reference(contrats, jour)
        total += reference if minutes >= SEUIL_DEMI_JOURNEE else reference / 2
    return total


def Calculer(mois=None, collaborateurs=[], realise=True, duree_legale=35, rattachement="FIN"):
    """ Eléments variables de paie du mois pour une liste de collaborateurs (instances). Renvoie un dictionnaire de résultats. """
    date_debut, date_fin = Limites_mois(mois)
    dates_mois = [date_debut + datetime.timedelta(days=n) for n in range((date_fin - date_debut).days + 1)]
    semaines = Semaines_du_mois(date_debut, date_fin, rattachement)
    debut_lecture = min([date_debut] + [lundi for lundi, dimanche in semaines])
    fin_lecture = max([date_fin] + [dimanche for lundi, dimanche in semaines])
    aujourdhui = datetime.datetime.now()

    collaborateurs = list(collaborateurs)
    ids = [collaborateur.pk for collaborateur in collaborateurs]
    liste_feries = list(Ferie.objects.all())
    categories = {categorie.pk: categorie for categorie in TypeEvenementCollaborateur.objects.all()}
    categories_absence = utils_absences.Get_categories_absence()
    types_conges = list(TypeCongeCollaborateur.objects.select_related("categorie").order_by("ordre", "nom"))
    ids_categories_conges = {type_conge.categorie_id for type_conge in types_conges}
    autres_absences = [categorie for idcategorie, categorie in categories_absence.items() if idcategorie not in ids_categories_conges]

    contrats = {}
    for contrat in ContratCollaborateur.objects.select_related("type_contrat", "type_poste").filter(collaborateur_id__in=ids).order_by("date_debut"):
        contrats.setdefault(contrat.collaborateur_id, []).append(contrat)

    # Evènements de travail (temps comptabilisé) par collaborateur et par jour
    travail = {}
    non_realises = {}
    evenements_absence = {}
    for evenement in utils_planning.Get_evenements(debut_lecture, fin_lecture, ids):
        categorie = categories.get(evenement.type_evenement_id)
        if not categorie:
            continue
        if categorie.pk in categories_absence and date_debut <= evenement.date_debut.date() <= date_fin:
            evenements_absence.setdefault(evenement.collaborateur_id, []).append(evenement)
        if categorie.type != "ADDITION":
            continue
        minutes, debut, fin = Duree_retenue(evenement, realise)
        travail.setdefault(evenement.collaborateur_id, []).append({"date": evenement.date_debut.date(), "minutes": minutes, "debut": debut, "fin": fin})
        if realise and not evenement.realise_debut and evenement.date_fin < aujourdhui and date_debut <= evenement.date_debut.date() <= date_fin:
            non_realises[evenement.collaborateur_id] = non_realises.get(evenement.collaborateur_id, 0) + 1

    # Congés décomptés sur le mois (même calcul que les compteurs de congés)
    periode_mois = {"debut": date_debut, "fin": date_fin}
    conges = {type_conge.pk: utils_conges.Calculer_poses(type_conge, ids, periode_mois, liste_feries) for type_conge in types_conges}

    # Autres absences : jours (demi-journées) et heures
    minutes_absences = utils_absences.Get_minutes_par_jour(ids, date_debut, date_fin, [categorie.pk for categorie in autres_absences])

    # Demandes d'absence et heures déclarées en attente
    demandes_attente = {}
    for demande in DemandeAbsenceCollaborateur.objects.filter(collaborateur_id__in=ids, etat="ATTENTE", date_debut__lte=date_fin, date_fin__gte=date_debut):
        demandes_attente[demande.collaborateur_id] = demandes_attente.get(demande.collaborateur_id, 0) + 1
    declarations_attente = {}
    for idcollaborateur in EvenementCollaborateur.objects.filter(collaborateur_id__in=ids, declare_etat="ATTENTE", date_debut__date__gte=date_debut,
                                                                 date_debut__date__lte=date_fin).values_list("collaborateur_id", flat=True):
        declarations_attente[idcollaborateur] = declarations_attente.get(idcollaborateur, 0) + 1

    lignes = []
    for collaborateur in collaborateurs:
        liste_contrats = contrats.get(collaborateur.pk, [])
        situation = [contrat for contrat in liste_contrats if contrat.date_debut <= date_fin and (not contrat.date_fin or contrat.date_fin >= date_debut)]
        contrat = situation[-1] if situation else None
        evenements_travail = travail.get(collaborateur.pk, [])

        # Totaux du mois
        du_mois = [item for item in evenements_travail if date_debut <= item["date"] <= date_fin]
        ligne = {
            "collaborateur": collaborateur, "contrat": contrat,
            "poste": contrat.type_poste.nom if contrat else "", "type_contrat": contrat.type_contrat.nom if contrat and contrat.type_contrat else "",
            "heures_hebdo": float(contrat.heures_hebdo) if contrat and contrat.heures_hebdo else None,
            "mode": contrat.get_objectif_mode_display() if contrat else "",
            "jours_travailles": len({item["date"] for item in du_mois if item["minutes"] > 0}),
            "travaille": sum(item["minutes"] for item in du_mois),
            "attendu": utils_planning.Heures_attendues(liste_contrats, dates_mois, liste_feries),
            "dimanche": sum(item["minutes"] for item in du_mois if item["debut"].weekday() == 6),
            "ferie": sum(item["minutes"] for item in du_mois if utils_dates.EstFerie(item["debut"].date(), liste_feries)),
            "nuit": sum(utils_planning.Minutes_dans_plage(item["debut"], item["fin"], 21, 6) for item in du_mois),
            "hc10": 0.0, "hc25": 0.0, "hs25": 0.0, "hs50": 0.0, "semaines": [], "alertes": [],
        }
        # Absences comptées comme du temps de travail (catégories « compter comme temps de travail », mêmes règles que l'objectif annuel)
        ligne["assimile"] = Minutes_assimilees(evenements_absence.get(collaborateur.pk, []), categories, liste_contrats)
        ligne["ecart"] = ligne["travaille"] + ligne["assimile"] - ligne["attendu"] if ligne["attendu"] else None

        # Heures complémentaires et supplémentaires par semaine
        hors_calcul = False
        for lundi, dimanche in semaines:
            minutes = sum(item["minutes"] for item in evenements_travail if lundi <= item["date"] <= dimanche)
            semaine = Calculer_semaine(minutes, liste_contrats, lundi, dimanche, duree_legale)
            if semaine is None:
                if Contrat_semaine(liste_contrats, lundi, dimanche):
                    hors_calcul = True
                continue
            ligne["semaines"].append(semaine)
            for cle in ("hc10", "hc25", "hs25", "hs50"):
                ligne[cle] += semaine[cle]
            if semaine["alerte"]:
                ligne["alertes"].append("Semaine du %s : %s" % (lundi.strftime("%d/%m"), semaine["alerte"].lower()))
        if hors_calcul:
            ligne["alertes"].append("Contrat %s : heures supplémentaires suivies par l'objectif annuel" % (ligne["mode"].lower() or "sans volume hebdomadaire"))

        # Congés et autres absences
        ligne["conges"] = [conges[type_conge.pk].get(collaborateur.pk, 0) for type_conge in types_conges]
        ligne["absences"] = []
        for categorie in autres_absences:
            jours, minutes_total = 0.0, 0.0
            for date in dates_mois:
                valeurs = minutes_absences.get((collaborateur.pk, date), {}).get(categorie.pk)
                if valeurs:
                    minutes_total += valeurs["minutes"]
                    portion = utils_absences.Portion_journee(valeurs["minutes"], valeurs["debut"], valeurs["fin"], utils_conges.Minutes_reference(liste_contrats, date))
                    jours += 1 if portion == "JOURNEE" else 0.5
            ligne["absences"].append({"jours": jours, "minutes": minutes_total})
        ligne["evenements_absence"] = evenements_absence.get(collaborateur.pk, [])

        # Points à vérifier
        if non_realises.get(collaborateur.pk):
            ligne["alertes"].append("%d évènement(s) passé(s) sans réalisé saisi (planifié retenu)" % non_realises[collaborateur.pk])
        if demandes_attente.get(collaborateur.pk):
            ligne["alertes"].append("%d demande(s) d'absence en attente de validation" % demandes_attente[collaborateur.pk])
        if declarations_attente.get(collaborateur.pk):
            ligne["alertes"].append("%d déclaration(s) d'heures en attente de validation" % declarations_attente[collaborateur.pk])
        if not contrat:
            ligne["alertes"].append("Aucun contrat sur le mois")
        lignes.append(ligne)

    # Colonnes d'absences utilisées par au moins un collaborateur
    index_conges = [index for index, type_conge in enumerate(types_conges) if any(ligne["conges"][index] for ligne in lignes)]
    index_absences = [index for index, categorie in enumerate(autres_absences) if any(ligne["absences"][index]["minutes"] for ligne in lignes)]
    return {
        "date_debut": date_debut, "date_fin": date_fin, "semaines": semaines, "lignes": lignes, "realise": realise, "duree_legale": duree_legale,
        "colonnes_conges": [{"index": index, "nom": types_conges[index].nom, "unite": types_conges[index].unite} for index in index_conges],
        "colonnes_absences": [{"index": index, "nom": autres_absences[index].nom} for index in index_absences],
        "categories": categories,
    }


# ------------------------------------------------- Export Excel -------------------------------------------------

def Exporter_excel(resultats={}, format_heures="DECIMAL"):
    """ Fichier Excel des éléments variables de paie. Renvoie l'URL du fichier. """
    import os, uuid, xlsxwriter
    from django.conf import settings
    from core.utils import utils_fichiers

    date_debut = resultats["date_debut"]
    utils_fichiers.GetTempRep()
    rep_base = os.path.join("temp", str(uuid.uuid4()))
    os.makedirs(os.path.join(settings.MEDIA_ROOT, rep_base))
    nom_fichier = "Variables_paie_%s.xlsx" % date_debut.strftime("%Y_%m")
    classeur = xlsxwriter.Workbook(os.path.join(settings.MEDIA_ROOT, rep_base, nom_fichier))
    f_titre = classeur.add_format({"bold": True, "font_size": 14})
    f_entete = classeur.add_format({"bold": True, "bg_color": "#EEF1F5", "border": 1, "text_wrap": True, "valign": "vcenter"})
    f_texte = classeur.add_format({"border": 1})
    f_nombre = classeur.add_format({"border": 1, "num_format": "0.##"})
    f_date = classeur.add_format({"num_format": "dd/mm/yyyy", "border": 1})
    f_date_heure = classeur.add_format({"num_format": "dd/mm/yyyy hh:mm", "border": 1})
    if format_heures == "DECIMAL":
        f_heures = classeur.add_format({"border": 1, "num_format": "0.00"})
        f_ecart = classeur.add_format({"border": 1, "num_format": "0.00;-0.00", "bold": True})
        convertir = lambda minutes: round(minutes / 60.0, 2)
    else:
        f_heures = classeur.add_format({"border": 1, "num_format": "[h]:mm"})
        f_ecart = classeur.add_format({"border": 1, "num_format": "[h]:mm;-[h]:mm", "bold": True})
        convertir = lambda minutes: minutes / 1440.0

    def Ecrire_entetes(feuille, ligne, colonnes):
        for index, (titre, largeur) in enumerate(colonnes):
            feuille.write(ligne, index, titre, f_entete)
            feuille.set_column(index, index, largeur)
        feuille.set_row(ligne, 45)

    # Feuille principale
    feuille = classeur.add_worksheet("Variables de paie")
    noms_mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    feuille.write(0, 0, "Éléments variables de paie - %s %d" % (noms_mois[date_debut.month - 1], date_debut.year), f_titre)
    feuille.write(1, 0, "Heures en %s. Heures retenues : %s. Écart = heures travaillées + absences assimilées - heures attendues. Heures complémentaires et supplémentaires calculées par semaine (durée légale : %s h), semaines rattachées au mois listées dans la feuille Semaines." % (
        "heures décimales" if format_heures == "DECIMAL" else "heures:minutes", "réalisé si saisi, sinon planifié" if resultats["realise"] else "planifié",
        ("%g" % resultats["duree_legale"]).replace(".", ",")))
    colonnes = [("Nom", 18), ("Prénom", 16), ("Poste", 18), ("Type de contrat", 14), ("Contrat (h/sem.)", 9), ("Jours travaillés", 9), ("Heures travaillées", 10),
                ("Absences assimilées", 10), ("Heures attendues", 10), ("Écart", 9), ("HC +10 %", 9), ("HC +25 %", 9), ("HS +25 %", 9), ("HS +50 %", 9), ("Dimanches", 9), ("Jours fériés", 9), ("Nuit (21h-6h)", 9)]
    colonnes += [("%s (%s)" % (colonne["nom"], "h" if colonne["unite"] == "HEURES" else "j"), 11) for colonne in resultats["colonnes_conges"]]
    for colonne in resultats["colonnes_absences"]:
        colonnes += [("%s (j)" % colonne["nom"], 10), ("%s (h)" % colonne["nom"], 10)]
    colonnes.append(("Points à vérifier", 60))
    Ecrire_entetes(feuille, 3, colonnes)

    ligne_excel = 4
    for ligne in resultats["lignes"]:
        collaborateur = ligne["collaborateur"]
        valeurs = [(collaborateur.nom, f_texte), (collaborateur.prenom or "", f_texte), (ligne["poste"], f_texte), (ligne["type_contrat"], f_texte),
                   (ligne["heures_hebdo"] if ligne["heures_hebdo"] is not None else "", f_nombre), (ligne["jours_travailles"], f_nombre),
                   (convertir(ligne["travaille"]), f_heures), (convertir(ligne["assimile"]), f_heures), (convertir(ligne["attendu"]), f_heures),
                   (convertir(ligne["ecart"]) if ligne["ecart"] is not None else "", f_ecart)]
        valeurs += [(convertir(ligne[cle]), f_heures) for cle in ("hc10", "hc25", "hs25", "hs50", "dimanche", "ferie", "nuit")]
        for colonne in resultats["colonnes_conges"]:
            valeur = ligne["conges"][colonne["index"]]
            valeurs.append((convertir(valeur * 60) if colonne["unite"] == "HEURES" else valeur, f_heures if colonne["unite"] == "HEURES" else f_nombre))
        for colonne in resultats["colonnes_absences"]:
            absence = ligne["absences"][colonne["index"]]
            valeurs += [(absence["jours"], f_nombre), (convertir(absence["minutes"]), f_heures)]
        valeurs.append(("\n".join(ligne["alertes"]), f_texte))
        for index, (valeur, format_cellule) in enumerate(valeurs):
            feuille.write(ligne_excel, index, valeur, format_cellule)
        ligne_excel += 1
    feuille.autofilter(3, 0, max(ligne_excel - 1, 4), len(colonnes) - 1)
    feuille.freeze_panes(4, 2)

    # Détail par semaine
    feuille = classeur.add_worksheet("Semaines")
    colonnes = [("Nom", 18), ("Prénom", 16), ("Semaine du", 11), ("au", 11), ("Contrat (h/sem.)", 9), ("Référence", 10), ("Travaillé", 10), ("Dépassement", 10),
                ("HC +10 %", 9), ("HC +25 %", 9), ("HS +25 %", 9), ("HS +50 %", 9), ("Remarque", 40)]
    Ecrire_entetes(feuille, 0, colonnes)
    ligne_excel = 1
    for ligne in resultats["lignes"]:
        for semaine in ligne["semaines"]:
            valeurs = [(ligne["collaborateur"].nom, f_texte), (ligne["collaborateur"].prenom or "", f_texte),
                       (datetime.datetime.combine(semaine["lundi"], datetime.time(0)), f_date), (datetime.datetime.combine(semaine["dimanche"], datetime.time(0)), f_date),
                       (float(semaine["contrat"].heures_hebdo), f_nombre)]
            valeurs += [(convertir(semaine[cle]), f_heures) for cle in ("reference", "travaille", "depassement", "hc10", "hc25", "hs25", "hs50")]
            valeurs.append((semaine["alerte"], f_texte))
            for index, (valeur, format_cellule) in enumerate(valeurs):
                if format_cellule is f_date:
                    feuille.write_datetime(ligne_excel, index, valeur, format_cellule)
                else:
                    feuille.write(ligne_excel, index, valeur, format_cellule)
            ligne_excel += 1
    feuille.autofilter(0, 0, max(ligne_excel - 1, 1), len(colonnes) - 1)
    feuille.freeze_panes(1, 2)

    # Détail des absences
    feuille = classeur.add_worksheet("Absences")
    colonnes = [("Nom", 18), ("Prénom", 16), ("Catégorie", 22), ("Début", 16), ("Fin", 16), ("Durée", 10), ("Titre", 30)]
    Ecrire_entetes(feuille, 0, colonnes)
    ligne_excel = 1
    categories = resultats["categories"]
    for ligne in resultats["lignes"]:
        for evenement in ligne["evenements_absence"]:
            categorie = categories.get(evenement.type_evenement_id)
            feuille.write(ligne_excel, 0, ligne["collaborateur"].nom, f_texte)
            feuille.write(ligne_excel, 1, ligne["collaborateur"].prenom or "", f_texte)
            feuille.write(ligne_excel, 2, categorie.nom if categorie else "", f_texte)
            feuille.write_datetime(ligne_excel, 3, evenement.date_debut, f_date_heure)
            feuille.write_datetime(ligne_excel, 4, evenement.date_fin, f_date_heure)
            feuille.write(ligne_excel, 5, convertir((evenement.date_fin - evenement.date_debut).total_seconds() / 60), f_heures)
            feuille.write(ligne_excel, 6, evenement.titre or "", f_texte)
            ligne_excel += 1
    feuille.autofilter(0, 0, max(ligne_excel - 1, 1), len(colonnes) - 1)
    feuille.freeze_panes(1, 2)

    classeur.close()
    return os.path.join(settings.MEDIA_URL, rep_base, nom_fichier)
