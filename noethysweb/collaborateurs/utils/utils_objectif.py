# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Calcul de l'objectif de temps de travail des collaborateurs (planning individuel) :
    - objectif d'une période de référence selon le mode de chaque contrat (hebdomadaire, annualisé, volume fixe, forfait jours, aucun),
    - ajustements manuels et reports de solde,
    - temps planifié selon les règles des catégories d'évènements. """

import datetime, decimal, calendar
from core.models import ContratCollaborateur, TypeEvenementCollaborateur, AjustementObjectifCollaborateur, Ferie
from core.utils import utils_parametres, utils_dates, utils_historique

CATEGORIE_PARAMETRES = "planning_objectifs"
PARAMETRES_DEFAUT = {"volume_annuel": 1607.0, "temps_plein": 35.0, "forfait_jours": 218.0, "periode": "CIVILE", "mois_debut_scolaire": 9}
LIMITES_PARAMETRES = {"volume_annuel": (1, 5000), "temps_plein": (1, 80), "forfait_jours": (1, 366), "mois_debut_scolaire": (1, 12)}
SEUIL_DEMI_JOURNEE = 240    # minutes : en dessous, une journée forfaitaire compte pour une demi-journée


# ------------------------------------------------- Paramètres généraux -------------------------------------------------

def Nettoyer_parametres(parametres={}):
    resultat = dict(PARAMETRES_DEFAUT)
    for nom, defaut in PARAMETRES_DEFAUT.items():
        if nom not in parametres or parametres[nom] in (None, ""):
            continue
        try:
            if nom == "periode":
                valeur = parametres[nom] if parametres[nom] in ("CIVILE", "SCOLAIRE") else defaut
            elif nom == "mois_debut_scolaire":
                valeur = int(parametres[nom])
            else:
                valeur = float(str(parametres[nom]).replace(",", "."))
        except (TypeError, ValueError):
            continue
        if nom in LIMITES_PARAMETRES:
            mini, maxi = LIMITES_PARAMETRES[nom]
            valeur = max(mini, min(maxi, valeur))
        resultat[nom] = valeur
    return resultat


def Get_parametres():
    return Nettoyer_parametres(utils_parametres.Get_categorie(categorie=CATEGORIE_PARAMETRES, utilisateur=None, parametres=PARAMETRES_DEFAUT))


def Set_parametres(parametres={}):
    parametres = Nettoyer_parametres(parametres)
    utils_parametres.Set_categorie(categorie=CATEGORIE_PARAMETRES, utilisateur=None, parametres=parametres)
    return parametres


# ------------------------------------------------- Périodes de référence -------------------------------------------------

def Get_periode(annee=None, type_periode="CIVILE", parametres=None):
    """ Renvoie la période de référence {debut, fin, libelle, annee, type} """
    parametres = parametres or Get_parametres()
    mois = int(parametres["mois_debut_scolaire"])
    if type_periode == "SCOLAIRE" and mois != 1:
        debut = datetime.date(annee, mois, 1)
        fin = datetime.date(annee + 1, mois - 1, calendar.monthrange(annee + 1, mois - 1)[1])
        libelle = "%d-%d" % (annee, annee + 1)
    else:
        type_periode = "CIVILE"
        debut, fin = datetime.date(annee, 1, 1), datetime.date(annee, 12, 31)
        libelle = str(annee)
    return {"debut": debut, "fin": fin, "libelle": libelle, "annee": annee, "type": type_periode}


def Annee_periode(date=None, type_periode="CIVILE", parametres=None):
    """ Année de début de la période de référence qui contient la date """
    parametres = parametres or Get_parametres()
    mois = int(parametres["mois_debut_scolaire"])
    if type_periode == "SCOLAIRE" and mois != 1 and date.month < mois:
        return date.year - 1
    return date.year


def Periode_suivante(periode=None, parametres=None):
    return Get_periode(periode["annee"] + 1, periode["type"], parametres)


def Type_periode_defaut(idcollaborateur=None, parametres=None, date=None):
    """ Type de période à afficher par défaut : celui du contrat en cours (ou du dernier contrat), sinon le paramètre général """
    parametres = parametres or Get_parametres()
    date = date or datetime.date.today()
    contrats = list(ContratCollaborateur.objects.filter(collaborateur_id=idcollaborateur).order_by("date_debut"))
    en_cours = [contrat for contrat in contrats if contrat.date_debut <= date and (not contrat.date_fin or contrat.date_fin >= date)]
    contrat = (en_cours or contrats[-1:] or [None])[-1]
    if contrat and contrat.objectif_periode:
        return contrat.objectif_periode
    return parametres["periode"]


# ------------------------------------------------- Outils -------------------------------------------------

def Nbre_jours(debut=None, fin=None):
    return max(0, (fin - debut).days + 1) if debut and fin else 0


def Jours_ouvres(debut=None, fin=None, liste_feries=[]):
    """ Liste des jours du lundi au vendredi hors jours fériés """
    jours = []
    date = debut
    while date and date <= fin:
        if date.weekday() < 5 and not utils_dates.EstFerie(date, liste_feries):
            jours.append(date)
        date += datetime.timedelta(days=1)
    return jours


def Format_heures(heures=0.0):
    signe = "-" if heures < 0 else ""
    minutes = int(round(abs(heures) * 60))
    return "%s%dh%02d" % (signe, minutes // 60, minutes % 60)


def Format_valeur(valeur=0.0, unite="heures"):
    if unite == "jours":
        texte = ("%.1f" % valeur).replace(".0", "").replace(".", ",")
        return "%s j" % texte
    return Format_heures(valeur)


def Format_nombre(valeur=0.0):
    return ("%.2f" % valeur).rstrip("0").rstrip(".").replace(".", ",")


# ------------------------------------------------- Calcul -------------------------------------------------

class Calcul_objectif():
    """ Objectif et temps planifié d'un collaborateur sur une période de référence """

    def __init__(self, idcollaborateur=None, periode=None, parametres=None, date_reference=None, contrats=None, ajustements=None, evenements=None,
                 categories=None, liste_feries=None, calculer_planifie=True):
        self.idcollaborateur = idcollaborateur
        self.periode = periode
        self.parametres = parametres or Get_parametres()
        self.date_reference = date_reference or datetime.date.today()
        self.liste_feries = liste_feries if liste_feries is not None else list(Ferie.objects.all())
        self.categories = categories if categories is not None else {categorie.pk: categorie for categorie in TypeEvenementCollaborateur.objects.all()}
        debut, fin = periode["debut"], periode["fin"]
        if contrats is None:
            contrats = ContratCollaborateur.objects.select_related("type_poste").filter(collaborateur_id=idcollaborateur, date_debut__lte=fin).order_by("date_debut")
        self.contrats = [contrat for contrat in contrats if contrat.date_debut <= fin and (not contrat.date_fin or contrat.date_fin >= debut)]
        if ajustements is None:
            ajustements = AjustementObjectifCollaborateur.objects.filter(collaborateur_id=idcollaborateur, date__gte=debut, date__lte=fin).order_by("date", "pk")
        self.ajustements = list(ajustements)

        self.Calculer_objectif()
        self.planifie = self.planifie_a_date = 0.0
        if calculer_planifie:
            if evenements is None:
                from collaborateurs.utils.utils_planning import Get_evenements
                evenements = Get_evenements(debut, fin, [idcollaborateur])
            self.Calculer_planifie(evenements)

    # ---------------------------------------------------------------- Objectif
    def Calculer_objectif(self):
        P = self.periode
        nbre_jours_periode = Nbre_jours(P["debut"], P["fin"])
        limite = min(self.date_reference, P["fin"])
        self.detail = []
        self.avertissements = []
        heures = {"total": 0.0, "a_date": 0.0}
        jours = {"total": 0.0, "a_date": 0.0}
        self.jours_ouvres_objectif = set()     # jours ouvrés couverts par un contrat avec objectif en heures (pour le forfait journalier)
        self.contrats_objectif = []

        for contrat in self.contrats:
            mode = contrat.objectif_mode or "HEBDO"
            debut = max(contrat.date_debut, P["debut"])
            fin = min(contrat.date_fin or P["fin"], P["fin"])
            fin_a_date = min(fin, limite)
            nbre_jours = Nbre_jours(debut, fin)
            nbre_jours_a_date = Nbre_jours(debut, fin_a_date) if fin_a_date >= debut else 0
            texte_contrat = "%s du %s au %s" % (contrat.type_poste.nom if contrat.type_poste_id else "Contrat", debut.strftime("%d/%m/%Y"), fin.strftime("%d/%m/%Y"))
            hebdo = float(contrat.heures_hebdo) if contrat.heures_hebdo else None
            volume = float(contrat.objectif_volume) if contrat.objectif_volume is not None else None

            if mode == "AUCUN":
                self.detail.append({"texte": "%s : aucun objectif" % texte_contrat, "valeur": None})
                continue

            if mode == "FORFAIT_JOURS":
                nbre = volume if volume else self.parametres["forfait_jours"]
                valeur = nbre * nbre_jours / nbre_jours_periode
                jours["total"] += valeur
                jours["a_date"] += nbre * nbre_jours_a_date / nbre_jours_periode
                self.detail.append({"texte": "%s : forfait %s jours × %d/%d jours" % (texte_contrat, Format_nombre(nbre), nbre_jours, nbre_jours_periode), "valeur": valeur, "unite": "jours"})
                self.contrats_objectif.append(contrat)
                continue

            if mode == "HEBDO":
                if not hebdo:
                    self.avertissements.append("%s : le volume horaire hebdomadaire n'est pas renseigné." % texte_contrat)
                    continue
                ouvres = Jours_ouvres(debut, fin, self.liste_feries)
                valeur = hebdo / 5 * len(ouvres)
                heures["total"] += valeur
                heures["a_date"] += hebdo / 5 * len([date for date in ouvres if date <= limite])
                self.detail.append({"texte": "%s : %s h / 5 × %d jours ouvrés" % (texte_contrat, Format_nombre(hebdo), len(ouvres)), "valeur": valeur, "unite": "heures"})

            elif mode == "ANNUALISE":
                volume_annuel = volume if volume else self.parametres["volume_annuel"]
                temps_plein = self.parametres["temps_plein"]
                quotite = hebdo / temps_plein if hebdo else 1.0
                valeur = volume_annuel * quotite * nbre_jours / nbre_jours_periode
                heures["total"] += valeur
                heures["a_date"] += volume_annuel * quotite * nbre_jours_a_date / nbre_jours_periode
                texte_quotite = " × %s %% (%s h / %s h)" % (Format_nombre(quotite * 100), Format_nombre(hebdo), Format_nombre(temps_plein)) if hebdo else ""
                self.detail.append({"texte": "%s : annualisé %s h%s × %d/%d jours" % (texte_contrat, Format_nombre(volume_annuel), texte_quotite, nbre_jours, nbre_jours_periode),
                                    "valeur": valeur, "unite": "heures"})

            elif mode == "VOLUME":
                if not volume:
                    self.avertissements.append("%s : le volume de référence n'est pas renseigné." % texte_contrat)
                    continue
                if contrat.date_fin:
                    duree_contrat = Nbre_jours(contrat.date_debut, contrat.date_fin)
                    texte = "%s : volume fixe %s h × %d/%d jours du contrat" % (texte_contrat, Format_nombre(volume), nbre_jours, duree_contrat)
                else:
                    duree_contrat = nbre_jours_periode
                    texte = "%s : volume fixe %s h par période × %d/%d jours" % (texte_contrat, Format_nombre(volume), nbre_jours, nbre_jours_periode)
                valeur = volume * nbre_jours / duree_contrat
                heures["total"] += valeur
                heures["a_date"] += volume * nbre_jours_a_date / duree_contrat
                self.detail.append({"texte": texte, "valeur": valeur, "unite": "heures"})

            self.contrats_objectif.append(contrat)
            for date in Jours_ouvres(debut, fin, self.liste_feries):
                self.jours_ouvres_objectif.add(date)

        # Unité : jours si tous les contrats avec objectif sont au forfait jours
        modes = {contrat.objectif_mode for contrat in self.contrats_objectif}
        if modes and modes == {"FORFAIT_JOURS"}:
            self.unite = "jours"
            base = jours
        else:
            self.unite = "heures"
            base = heures
            if "FORFAIT_JOURS" in modes:
                self.avertissements.append("Les contrats au forfait jours sont ignorés car la période comporte aussi des contrats en heures.")
                self.detail = [ligne for ligne in self.detail if ligne.get("unite") != "jours"]

        self.objectif_contrats = base["total"]
        self.objectif_contrats_a_date = base["a_date"]
        self.a_objectif = bool(self.contrats_objectif)

        # Ajustements et reports
        self.total_ajustements = 0.0
        self.total_ajustements_a_date = 0.0
        for ajustement in self.ajustements:
            valeur = float(ajustement.valeur)
            self.total_ajustements += valeur
            if ajustement.date <= limite:
                self.total_ajustements_a_date += valeur

        self.objectif = self.objectif_contrats + self.total_ajustements
        self.objectif_a_date = self.objectif_contrats_a_date + self.total_ajustements_a_date

        # Durée forfaitaire journalière (catégories "compter comme temps de travail : durée forfaitaire")
        self.forfait_journalier = self.objectif_contrats / len(self.jours_ouvres_objectif) if self.unite == "heures" and self.jours_ouvres_objectif else 0.0

    # ---------------------------------------------------------------- Planifié
    def Regle_categorie(self, idcategorie=None):
        """ Renvoie 1, -1, 0 ou 'FORFAIT' """
        categorie = self.categories.get(idcategorie)
        if not categorie:
            return 0
        if categorie.temps_travail_objectif == "DUREE":
            return 1
        if categorie.temps_travail_objectif == "FORFAIT":
            return "FORFAIT"
        return {"ADDITION": 1, "SOUSTRACTION": -1}.get(categorie.type, 0)

    def Calculer_planifie(self, evenements=[]):
        P = self.periode
        debut_p = datetime.datetime.combine(P["debut"], datetime.time(0))
        fin_p = datetime.datetime.combine(P["fin"] + datetime.timedelta(days=1), datetime.time(0))
        limite = datetime.datetime.combine(min(self.date_reference, P["fin"]) + datetime.timedelta(days=1), datetime.time(0))

        minutes_par_jour = {}       # date -> minutes comptées (règles 1/-1)
        forfaits_par_jour = {}      # date -> minutes des évènements au forfait
        positifs_par_jour = {}      # date -> minutes positives (forfait jours)
        for evenement in evenements:
            if not evenement.date_debut or not evenement.date_fin:
                continue
            regle = self.Regle_categorie(evenement.type_evenement_id)
            if regle == 0:
                continue
            # Découpage par jour
            debut = max(evenement.date_debut, debut_p)
            fin = min(evenement.date_fin, fin_p)
            while debut < fin:
                minuit = datetime.datetime.combine(debut.date() + datetime.timedelta(days=1), datetime.time(0))
                morceau = (min(fin, minuit) - debut).total_seconds() / 60
                jour = debut.date()
                if regle == "FORFAIT":
                    forfaits_par_jour[jour] = forfaits_par_jour.get(jour, 0) + morceau
                else:
                    minutes_par_jour[jour] = minutes_par_jour.get(jour, 0) + regle * morceau
                    if regle > 0:
                        positifs_par_jour[jour] = positifs_par_jour.get(jour, 0) + morceau
                debut = minuit

        self.planifie_par_jour = {}
        if self.unite == "jours":
            for jour in set(positifs_par_jour) | set(forfaits_par_jour):
                minutes = positifs_par_jour.get(jour, 0) + forfaits_par_jour.get(jour, 0)
                if minutes > 0:
                    self.planifie_par_jour[jour] = 1.0 if minutes >= SEUIL_DEMI_JOURNEE else 0.5
        else:
            for jour, minutes in minutes_par_jour.items():
                self.planifie_par_jour[jour] = self.planifie_par_jour.get(jour, 0) + minutes / 60
            for jour, minutes in forfaits_par_jour.items():
                forfait = self.forfait_journalier if minutes >= SEUIL_DEMI_JOURNEE else self.forfait_journalier / 2
                self.planifie_par_jour[jour] = self.planifie_par_jour.get(jour, 0) + forfait

        self.planifie = sum(self.planifie_par_jour.values())
        self.planifie_a_date = sum(valeur for jour, valeur in self.planifie_par_jour.items() if jour < limite.date())

    # ---------------------------------------------------------------- Résultats
    @property
    def solde(self):
        return self.planifie - self.objectif

    def Get_dict(self):
        return {
            "a_objectif": self.a_objectif, "unite": self.unite,
            "objectif": round(self.objectif, 4), "objectif_a_date": round(self.objectif_a_date, 4),
            "objectif_contrats": round(self.objectif_contrats, 4), "total_ajustements": round(self.total_ajustements, 4),
            "planifie": round(self.planifie, 4), "planifie_a_date": round(self.planifie_a_date, 4),
            "forfait_journalier": round(self.forfait_journalier, 4), "seuil_demi_journee": SEUIL_DEMI_JOURNEE,
            "detail": [{"texte": ligne["texte"], "valeur": Format_valeur(ligne["valeur"], ligne.get("unite", "heures")) if ligne["valeur"] is not None else ""} for ligne in self.detail],
            "avertissements": self.avertissements,
            "ajustements": [Serialiser_ajustement(ajustement) for ajustement in self.ajustements],
            "periode": {"debut": str(self.periode["debut"]), "fin": str(self.periode["fin"]), "libelle": self.periode["libelle"], "annee": self.periode["annee"], "type": self.periode["type"]},
            "date_reference": str(self.date_reference),
        }


def Serialiser_ajustement(ajustement=None):
    return {"id": ajustement.pk, "date": str(ajustement.date), "valeur": float(ajustement.valeur), "type": ajustement.type, "motif": ajustement.motif or "",
            "origine": ajustement.periode_origine or ""}


# ------------------------------------------------- Report de solde -------------------------------------------------

def Reporter_solde(idcollaborateur=None, periode=None, parametres=None, utilisateur=None, calcul=None):
    """ Reporte le solde (planifié - objectif) de la période sur la période suivante, sous forme d'un ajustement de type REPORT.
        Un excédent réduit l'objectif suivant, un déficit l'augmente. Un report existant pour la même période d'origine est remplacé. """
    parametres = parametres or Get_parametres()
    calcul = calcul or Calcul_objectif(idcollaborateur=idcollaborateur, periode=periode, parametres=parametres, date_reference=periode["fin"])
    if not calcul.a_objectif:
        return None
    suivante = Periode_suivante(periode, parametres)
    valeur = decimal.Decimal(str(round(-calcul.solde, 2)))
    origine = "%s:%s" % (periode["type"], periode["libelle"])
    texte_unite = "jours" if calcul.unite == "jours" else "heures"
    if calcul.solde > 0:
        motif = "Report de l'excédent %s (%s)" % (periode["libelle"], Format_valeur(calcul.solde, calcul.unite))
    elif calcul.solde < 0:
        motif = "Report du déficit %s (%s)" % (periode["libelle"], Format_valeur(-calcul.solde, calcul.unite))
    else:
        motif = "Report du solde %s (nul)" % periode["libelle"]

    ajustement = AjustementObjectifCollaborateur.objects.filter(collaborateur_id=idcollaborateur, type="REPORT", periode_origine=origine).first()
    ancien = Format_valeur(float(ajustement.valeur), calcul.unite) if ajustement else None
    if not ajustement:
        ajustement = AjustementObjectifCollaborateur(collaborateur_id=idcollaborateur, type="REPORT", periode_origine=origine)
    ajustement.date = suivante["debut"]
    ajustement.valeur = valeur
    ajustement.motif = motif
    ajustement.utilisateur = utilisateur
    ajustement.save()

    utils_historique.Ajouter(titre="Report du solde de l'objectif", detail="%s : %s %s reportées sur %s" % (periode["libelle"], Format_valeur(float(valeur), calcul.unite), texte_unite, suivante["libelle"]),
                             old=ancien, utilisateur=utilisateur, collaborateur=idcollaborateur, objet="Ajustement d'objectif", idobjet=ajustement.pk, classe="AjustementObjectifCollaborateur")
    return ajustement
