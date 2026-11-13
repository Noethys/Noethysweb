# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, os, uuid
from django.conf import settings
from core.models import Collaborateur, TypeEvenementCollaborateur, ContratCollaborateur, Ferie
from core.utils import utils_dates, utils_fichiers
from collaborateurs.utils import utils_planning
from collaborateurs.utils.utils_affectations import Arbre


def Exporter(dates=[], collaborateurs=[]):
    """ Récapitulatif des heures pour la paie (fichier Excel). Renvoie l'URL du fichier. """
    import xlsxwriter

    categories = {categorie.pk: categorie for categorie in TypeEvenementCollaborateur.objects.all()}
    arbre = Arbre()
    liste_feries = list(Ferie.objects.all())
    dates_set = set(dates)
    liste_collaborateurs = list(Collaborateur.objects.filter(pk__in=collaborateurs).order_by("nom", "prenom"))
    contrats, postes = {}, {}
    for contrat in ContratCollaborateur.objects.select_related("type_poste").filter(collaborateur__in=liste_collaborateurs).order_by("date_debut"):
        contrats.setdefault(contrat.collaborateur_id, []).append(contrat)
        postes[contrat.collaborateur_id] = contrat.type_poste.nom
    evenements = {}
    for evenement in utils_planning.Get_evenements(dates[0], dates[-1], collaborateurs):
        if evenement.date_debut.date() in dates_set:
            evenements.setdefault(evenement.collaborateur_id, []).append(evenement)

    # Création du fichier
    utils_fichiers.GetTempRep()
    rep_base = os.path.join("temp", str(uuid.uuid4()))
    os.makedirs(os.path.join(settings.MEDIA_ROOT, rep_base))
    nom_fichier = "Recapitulatif_planning_%s_%s.xlsx" % (dates[0].strftime("%Y%m%d"), dates[-1].strftime("%Y%m%d"))
    classeur = xlsxwriter.Workbook(os.path.join(settings.MEDIA_ROOT, rep_base, nom_fichier))
    format_titre = classeur.add_format({"bold": True, "font_size": 14})
    format_entete = classeur.add_format({"bold": True, "bg_color": "#EEF1F5", "border": 1, "text_wrap": True, "valign": "vcenter"})
    format_heures = classeur.add_format({"num_format": "[h]:mm", "border": 1})
    format_heures_gras = classeur.add_format({"num_format": "[h]:mm", "border": 1, "bold": True})
    format_ecart = classeur.add_format({"num_format": "[h]:mm;-[h]:mm", "border": 1, "bold": True})
    format_texte = classeur.add_format({"border": 1})
    format_date = classeur.add_format({"num_format": "dd/mm/yyyy", "border": 1})
    format_heure = classeur.add_format({"num_format": "hh:mm", "border": 1})

    # Feuille récapitulatif
    feuille = classeur.add_worksheet("Récapitulatif")
    feuille.write(0, 0, "Récapitulatif des heures du %s au %s" % (utils_dates.ConvertDateToFR(dates[0]), utils_dates.ConvertDateToFR(dates[-1])), format_titre)
    feuille.write(1, 0, "Heures retenues : réalisé lorsqu'il est saisi, sinon planifié. Heures attendues : volume hebdomadaire du contrat / 5 par jour ouvré (hors fériés).")
    colonnes = [("Collaborateur", 26), ("Poste", 20), ("Contrat (h/sem.)", 11), ("Heures attendues", 11), ("Planifié", 11), ("Réalisé saisi", 11), ("Retenu", 11),
                ("Écart / contrat", 11), ("Au-delà du contrat (par semaine)", 14), ("Dont dimanches", 11), ("Dont jours fériés", 11), ("Dont nuit (21h-6h)", 11), ("Non comptabilisé", 12)]
    for index, (titre, largeur) in enumerate(colonnes):
        feuille.write(3, index, titre, format_entete)
        feuille.set_column(index, index, largeur)
    feuille.set_row(3, 42)

    ligne = 4
    for collaborateur in liste_collaborateurs:
        planifie = realise = retenu = dimanche = ferie = nuit = neutre = 0
        par_semaine = {}
        for evenement in evenements.get(collaborateur.pk, []):
            categorie = categories.get(evenement.type_evenement_id)
            if not categorie:
                continue
            duree_planifiee = utils_planning.Duree_comptabilisee(evenement, categorie)
            duree_realisee = utils_planning.Duree_comptabilisee(evenement, categorie, realise=True)
            planifie += duree_planifiee
            realise += duree_realisee
            duree_retenue = duree_realisee if evenement.realise_debut else duree_planifiee
            retenu += duree_retenue
            semaine = evenement.date_debut.date().isocalendar()[:2]
            par_semaine[semaine] = par_semaine.get(semaine, 0) + duree_retenue
            debut, fin = (evenement.realise_debut, evenement.realise_fin) if evenement.realise_debut else (evenement.date_debut, evenement.date_fin)
            if categorie.type == "NEUTRE":
                neutre += (fin - debut).total_seconds() / 60
                continue
            if categorie.type != "ADDITION":
                continue
            if debut.weekday() == 6:
                dimanche += duree_retenue
            if utils_dates.EstFerie(debut.date(), liste_feries):
                ferie += duree_retenue
            nuit += utils_planning.Minutes_dans_plage(debut, fin, 21, 6)

        # Heures attendues et dépassements par semaine
        attendu = utils_planning.Heures_attendues(contrats.get(collaborateur.pk, []), dates, liste_feries)
        depassement = 0
        for semaine, minutes in par_semaine.items():
            dates_semaine = [date for date in dates if date.isocalendar()[:2] == semaine]
            attendu_semaine = utils_planning.Heures_attendues(contrats.get(collaborateur.pk, []), dates_semaine, liste_feries)
            if attendu_semaine and minutes > attendu_semaine:
                depassement += minutes - attendu_semaine
        contrat_actuel = [contrat for contrat in contrats.get(collaborateur.pk, []) if contrat.heures_hebdo]
        heures_hebdo = float(contrat_actuel[-1].heures_hebdo) if contrat_actuel else None

        valeurs = [collaborateur.Get_nom(), postes.get(collaborateur.pk, ""), heures_hebdo, attendu, planifie, realise, retenu,
                   retenu - attendu if attendu else None, depassement, dimanche, ferie, nuit, neutre]
        for index, valeur in enumerate(valeurs):
            if index < 2:
                feuille.write(ligne, index, valeur, format_texte)
            elif index == 2:
                feuille.write(ligne, index, valeur if valeur is not None else "", format_texte)
            elif valeur is None:
                feuille.write(ligne, index, "", format_texte)
            else:
                feuille.write(ligne, index, valeur / 1440, format_ecart if index == 7 else (format_heures_gras if index == 6 else format_heures))
        ligne += 1
    feuille.freeze_panes(4, 1)

    # Feuille détail
    feuille = classeur.add_worksheet("Détail")
    colonnes = [("Collaborateur", 26), ("Date", 11), ("Début", 8), ("Fin", 8), ("Durée planifiée", 10), ("Début réalisé", 9), ("Fin réalisée", 9), ("Durée réalisée", 10),
                ("Catégorie", 18), ("Comptabilisation", 16), ("Affectation", 34), ("Titre", 30)]
    for index, (titre, largeur) in enumerate(colonnes):
        feuille.write(0, index, titre, format_entete)
        feuille.set_column(index, index, largeur)
    ligne = 1
    for collaborateur in liste_collaborateurs:
        for evenement in evenements.get(collaborateur.pk, []):
            categorie = categories.get(evenement.type_evenement_id)
            feuille.write(ligne, 0, collaborateur.Get_nom(), format_texte)
            feuille.write_datetime(ligne, 1, evenement.date_debut, format_date)
            feuille.write_datetime(ligne, 2, evenement.date_debut, format_heure)
            feuille.write_datetime(ligne, 3, evenement.date_fin, format_heure)
            feuille.write(ligne, 4, (evenement.date_fin - evenement.date_debut).total_seconds() / 86400, format_heures)
            if evenement.realise_debut:
                feuille.write_datetime(ligne, 5, evenement.realise_debut, format_heure)
                feuille.write_datetime(ligne, 6, evenement.realise_fin, format_heure)
                feuille.write(ligne, 7, (evenement.realise_fin - evenement.realise_debut).total_seconds() / 86400, format_heures)
            else:
                for index in (5, 6, 7):
                    feuille.write(ligne, index, "", format_texte)
            feuille.write(ligne, 8, categorie.nom if categorie else "", format_texte)
            feuille.write(ligne, 9, categorie.get_type_display() if categorie else "", format_texte)
            feuille.write(ligne, 10, arbre.Get_chemin(evenement.affectation_id) if evenement.affectation_id else "", format_texte)
            feuille.write(ligne, 11, evenement.titre or "", format_texte)
            ligne += 1
    feuille.autofilter(0, 0, max(ligne - 1, 1), len(colonnes) - 1)
    feuille.freeze_panes(1, 1)

    classeur.close()
    return os.path.join(settings.MEDIA_URL, rep_base, nom_fichier)


def Echapper_ical(texte=""):
    return (texte or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r\n", "\\n").replace("\n", "\\n")


def Plier_ligne_ical(ligne=""):
    """ Découpe les lignes de plus de 75 octets (RFC 5545) """
    resultat, courant = [], ""
    for caractere in ligne:
        if len((courant + caractere).encode("utf-8")) > 74:
            resultat.append(courant)
            courant = " "
        courant += caractere
    resultat.append(courant)
    return "\r\n".join(resultat)


def Generer_ical(collaborateur=None):
    """ Contenu iCalendar des évènements d'un collaborateur (60 jours passés, 365 jours à venir) """
    categories = {categorie.pk: categorie for categorie in TypeEvenementCollaborateur.objects.all()}
    arbre = Arbre()
    aujourdhui = datetime.date.today()
    maintenant = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fuseau = settings.TIME_ZONE
    lignes = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Noethysweb//Planning des collaborateurs//FR", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
              "X-WR-CALNAME:%s" % Echapper_ical("Planning - %s" % collaborateur.Get_nom()), "X-WR-TIMEZONE:%s" % fuseau]
    for evenement in utils_planning.Get_evenements(aujourdhui - datetime.timedelta(days=60), aujourdhui + datetime.timedelta(days=365), [collaborateur.pk]):
        categorie = categories.get(evenement.type_evenement_id)
        resume = evenement.titre or (categorie.nom if categorie else "Evènement")
        description = []
        if categorie:
            description.append(categorie.nom)
        if evenement.affectation_id:
            description.append(arbre.Get_chemin(evenement.affectation_id))
        lignes.extend([
            "BEGIN:VEVENT",
            "UID:evenement-collaborateur-%d@noethysweb" % evenement.pk,
            "DTSTAMP:%s" % maintenant,
            "SEQUENCE:%d" % evenement.version,
            "DTSTART;TZID=%s:%s" % (fuseau, evenement.date_debut.strftime("%Y%m%dT%H%M%S")),
            "DTEND;TZID=%s:%s" % (fuseau, evenement.date_fin.strftime("%Y%m%dT%H%M%S")),
            "SUMMARY:%s" % Echapper_ical(resume),
            "DESCRIPTION:%s" % Echapper_ical(" - ".join(description)),
            "END:VEVENT",
        ])
    lignes.append("END:VCALENDAR")
    return "\r\n".join(Plier_ligne_ical(ligne) for ligne in lignes) + "\r\n"


def Exporter_bilan(collaborateur=None, periode=None):
    """ Bilan annuel d'un collaborateur (planning individuel) : synthèse mensuelle avec objectif, évènements, ajustements. Renvoie l'URL du fichier. """
    import xlsxwriter
    from collaborateurs.utils import utils_objectif

    categories = {categorie.pk: categorie for categorie in TypeEvenementCollaborateur.objects.all()}
    arbre = Arbre()
    calcul = utils_objectif.Calcul_objectif(idcollaborateur=collaborateur.pk, periode=periode, categories=categories)
    en_jours = calcul.unite == "jours"
    evenements = list(utils_planning.Get_evenements(periode["debut"], periode["fin"], [collaborateur.pk]))

    utils_fichiers.GetTempRep()
    rep_base = os.path.join("temp", str(uuid.uuid4()))
    os.makedirs(os.path.join(settings.MEDIA_ROOT, rep_base))
    nom_fichier = "Bilan_planning_%s_%s.xlsx" % ("".join(c for c in collaborateur.Get_nom() if c.isalnum() or c in "-_") or collaborateur.pk, periode["libelle"])
    classeur = xlsxwriter.Workbook(os.path.join(settings.MEDIA_ROOT, rep_base, nom_fichier))
    f_titre = classeur.add_format({"bold": True, "font_size": 14})
    f_entete = classeur.add_format({"bold": True, "bg_color": "#EEF1F5", "border": 1, "text_wrap": True, "valign": "vcenter"})
    f_texte = classeur.add_format({"border": 1})
    f_gras = classeur.add_format({"border": 1, "bold": True})
    f_date = classeur.add_format({"num_format": "dd/mm/yyyy", "border": 1})
    f_heure = classeur.add_format({"num_format": "hh:mm", "border": 1})
    f_valeur = classeur.add_format({"num_format": "0.0" if en_jours else "[h]:mm;-[h]:mm", "border": 1})
    f_valeur_gras = classeur.add_format({"num_format": "0.0" if en_jours else "[h]:mm;-[h]:mm", "border": 1, "bold": True})
    f_duree = classeur.add_format({"num_format": "[h]:mm", "border": 1})
    convertir = (lambda v: v) if en_jours else (lambda v: v / 24)   # heures -> fraction de jour pour Excel
    unite = "jours" if en_jours else "heures"

    # Synthèse mensuelle
    feuille = classeur.add_worksheet("Synthèse")
    feuille.write(0, 0, "Bilan de l'objectif %s - %s" % (periode["libelle"], collaborateur.Get_nom()), f_titre)
    feuille.write(1, 0, "Valeurs en %s. Attendu : objectif des contrats réparti au prorata des jours du mois, plus les ajustements datés du mois." % unite)
    colonnes = [("Mois", 18), ("Planifié", 12), ("Attendu", 12), ("Écart du mois", 12), ("Écart cumulé", 12)]
    for index, (titre, largeur) in enumerate(colonnes):
        feuille.write(3, index, titre, f_entete)
        feuille.set_column(index, index, largeur)
    nbre_jours = (periode["fin"] - periode["debut"]).days + 1
    jours = [periode["debut"] + datetime.timedelta(days=n) for n in range(nbre_jours)]
    mois = []
    for jour in jours:
        if not mois or (jour.year, jour.month) != (mois[-1][0].year, mois[-1][0].month):
            mois.append([])
        mois[-1].append(jour)
    noms_mois = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    ligne, cumul = 4, 0.0
    for dates_mois in mois:
        planifie = sum(calcul.planifie_par_jour.get(date, 0) for date in dates_mois)
        attendu = calcul.objectif_contrats * len(dates_mois) / nbre_jours + sum(float(a.valeur) for a in calcul.ajustements if dates_mois[0] <= a.date <= dates_mois[-1])
        cumul += planifie - attendu
        feuille.write(ligne, 0, "%s %d" % (noms_mois[dates_mois[0].month - 1], dates_mois[0].year), f_texte)
        for colonne, valeur in enumerate((planifie, attendu, planifie - attendu, cumul), 1):
            feuille.write(ligne, colonne, convertir(valeur), f_valeur)
        ligne += 1
    feuille.write(ligne, 0, "Total", f_gras)
    for colonne, valeur in enumerate((calcul.planifie, calcul.objectif, calcul.planifie - calcul.objectif), 1):
        feuille.write(ligne, colonne, convertir(valeur), f_valeur_gras)
    feuille.write(ligne, 4, "", f_texte)
    ligne += 2
    feuille.write(ligne, 0, "Composition de l'objectif", f_gras)
    ligne += 1
    for detail in calcul.detail:
        if detail["valeur"] is None:
            continue
        feuille.write(ligne, 0, detail["texte"])
        feuille.write(ligne, 3, convertir(detail["valeur"]), f_valeur)
        ligne += 1
    for ajustement in calcul.ajustements:
        feuille.write(ligne, 0, "%s - %s" % (ajustement.date.strftime("%d/%m/%Y"), ajustement.motif or ajustement.get_type_display()))
        feuille.write(ligne, 3, convertir(float(ajustement.valeur)), f_valeur)
        ligne += 1
    feuille.write(ligne, 0, "Objectif de la période", f_gras)
    feuille.write(ligne, 3, convertir(calcul.objectif), f_valeur_gras)
    for texte in calcul.avertissements:
        ligne += 1
        feuille.write(ligne, 0, texte)

    # Evènements
    feuille = classeur.add_worksheet("Évènements")
    colonnes = [("Date", 11), ("Jour", 10), ("Début", 8), ("Fin", 8), ("Durée", 9), ("Catégorie", 20), ("Prise en compte", 22), ("Affectation", 34), ("Titre", 30),
                ("Début réalisé", 9), ("Fin réalisée", 9)]
    for index, (titre, largeur) in enumerate(colonnes):
        feuille.write(0, index, titre, f_entete)
        feuille.set_column(index, index, largeur)
    jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    ligne = 1
    for evenement in evenements:
        categorie = categories.get(evenement.type_evenement_id)
        regle = ""
        if categorie:
            regle = {"DUREE": "Compté comme travail", "FORFAIT": "Compté au forfait"}.get(categorie.temps_travail_objectif) or categorie.get_type_display()
        feuille.write_datetime(ligne, 0, evenement.date_debut, f_date)
        feuille.write(ligne, 1, jours_semaine[evenement.date_debut.weekday()], f_texte)
        feuille.write_datetime(ligne, 2, evenement.date_debut, f_heure)
        feuille.write_datetime(ligne, 3, evenement.date_fin, f_heure)
        feuille.write(ligne, 4, (evenement.date_fin - evenement.date_debut).total_seconds() / 86400, f_duree)
        feuille.write(ligne, 5, categorie.nom if categorie else "", f_texte)
        feuille.write(ligne, 6, regle, f_texte)
        feuille.write(ligne, 7, arbre.Get_chemin(evenement.affectation_id) if evenement.affectation_id else "", f_texte)
        feuille.write(ligne, 8, evenement.titre or "", f_texte)
        if evenement.realise_debut:
            feuille.write_datetime(ligne, 9, evenement.realise_debut, f_heure)
            feuille.write_datetime(ligne, 10, evenement.realise_fin, f_heure)
        else:
            feuille.write(ligne, 9, "", f_texte)
            feuille.write(ligne, 10, "", f_texte)
        ligne += 1
    feuille.autofilter(0, 0, max(ligne - 1, 1), len(colonnes) - 1)
    feuille.freeze_panes(1, 0)

    # Ajustements et reports
    feuille = classeur.add_worksheet("Ajustements")
    colonnes = [("Date d'effet", 12), ("Type", 18), ("Valeur", 12), ("Motif", 50)]
    for index, (titre, largeur) in enumerate(colonnes):
        feuille.write(0, index, titre, f_entete)
        feuille.set_column(index, index, largeur)
    for ligne, ajustement in enumerate(calcul.ajustements, 1):
        feuille.write_datetime(ligne, 0, datetime.datetime.combine(ajustement.date, datetime.time(0)), f_date)
        feuille.write(ligne, 1, ajustement.get_type_display(), f_texte)
        feuille.write(ligne, 2, convertir(float(ajustement.valeur)), f_valeur)
        feuille.write(ligne, 3, ajustement.motif or "", f_texte)

    classeur.close()
    return os.path.join(settings.MEDIA_URL, rep_base, nom_fichier)
