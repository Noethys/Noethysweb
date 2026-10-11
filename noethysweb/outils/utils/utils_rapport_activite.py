# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

"""
Moteur de calcul du rapport d'activité.

Produit une structure neutre (liste de rubriques contenant des blocs) indépendante du rendu :
    - kpis       : chiffres clés avec comparaison N-1
    - analyse    : paragraphes d'analyse rédigés automatiquement
    - tableau    : tableau de données (avec ligne de total optionnelle)
    - barres     : histogramme vertical ou horizontal (1 ou 2 séries)
    - courbe     : courbe (1 ou 2 séries)
    - camembert  : répartition
    - sous_titre : intertitre
    - note       : remarque méthodologique
"""

import logging, datetime, operator
logger = logging.getLogger(__name__)
from decimal import Decimal
from collections import Counter, defaultdict
from dateutil.relativedelta import relativedelta
from django.db.models import Q, Count, Sum
from core.models import Consommation, Inscription, Individu, Famille, Vacance, Ouverture, Remplissage, \
    UniteRemplissage, Evenement, Prestation, Deduction, Facture, Reglement, Ventilation, Rappel, Cotisation, Location, Transport, \
    Quotient, Scolarite, Historique, PortailRenseignement, PortailMessage, Paiement, Destinataire, DestinataireSMS, Mail, \
    Collaborateur, ContratCollaborateur, Depot, Groupe


# ------------------------------------------------------------------------------------------------------
# Liste des rubriques disponibles
# ------------------------------------------------------------------------------------------------------

RUBRIQUES = [
    ("synthese", "Synthèse et chiffres clés", "Indicateurs principaux, faits marquants et évolution N-1"),
    ("activites", "Activités et offre d'accueil", "Jours d'ouverture, capacités et taux de remplissage"),
    ("inscriptions", "Inscriptions", "Inscriptions actives et nouvelles, par activité, groupe, tarif et statut"),
    ("public", "Public accueilli", "Genre, âges, nouveaux usagers, villes, secteurs, écoles et niveaux"),
    ("familles", "Familles", "Composition, quotients familiaux, caisses, régimes, ancienneté"),
    ("frequentation", "Fréquentation", "Consommations par mois, jour, activité, unité et groupe, pics"),
    ("absences", "Absences", "Absences justifiées et injustifiées, taux d'absentéisme"),
    ("evenements", "Événements", "Événements organisés, participants et remplissage"),
    ("prestations", "Prestations", "Montants, catégories, tarifs, déductions et aides"),
    ("facturation", "Facturation", "Factures émises, montants, soldes et impayés"),
    ("reglements", "Règlements", "Encaissements, modes de règlement, paiements en ligne et délais"),
    ("recouvrement", "Recouvrement", "Rappels, impayés et ancienneté des créances"),
    ("adhesions", "Adhésions", "Adhésions valides et nouvelles, types, montants"),
    ("locations", "Locations", "Locations de produits, durées et montants"),
    ("transports", "Transports", "Transports programmés, catégories et lignes"),
    ("portail", "Portail famille", "Comptes, connexions, réservations, demandes et messages"),
    ("communication", "Communication", "Emails et SMS envoyés"),
    ("personnel", "Personnel", "Collaborateurs, contrats et postes"),
    ("application", "Utilisation de l'application", "Actions des utilisateurs et volumétrie"),
]

RUBRIQUES_DEFAUT = ["synthese", "activites", "inscriptions", "public", "familles", "frequentation", "absences", "evenements",
                    "prestations", "facturation", "reglements", "recouvrement", "adhesions", "portail", "communication"]

MOIS_COURTS = ["Janv.", "Févr.", "Mars", "Avr.", "Mai", "Juin", "Juil.", "Août", "Sept.", "Oct.", "Nov.", "Déc."]
MOIS_LONGS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
TRANCHES_AGES = [(0, 2, "0-2 ans"), (3, 5, "3-5 ans"), (6, 11, "6-11 ans"), (12, 17, "12-17 ans"), (18, 25, "18-25 ans"), (26, 59, "26-59 ans"), (60, 200, "60 ans et +")]
TRANCHES_QF_DEFAUT = "0-500;501-800;801-1100;1101-1500;1501-99999"
ETATS_LABELS = {"reservation": "Réservation", "present": "Présent", "absenti": "Absence injustifiée", "absentj": "Absence justifiée",
                "attente": "Attente", "refus": "Refus", "demande": "Demande"}
NBRE_MAX_LIGNES = 15


# ------------------------------------------------------------------------------------------------------
# Formatage
# ------------------------------------------------------------------------------------------------------

def Format_nombre(valeur, format="entier", symbole="€"):
    """ Formate un nombre à la française """
    if valeur is None or valeur == "":
        return "-"
    if isinstance(valeur, str):
        return valeur
    try:
        if format == "entier":
            texte = "{:,.0f}".format(float(valeur))
        elif format == "decimal":
            texte = "{:,.1f}".format(float(valeur))
        elif format == "montant":
            texte = "{:,.2f}".format(float(valeur)) + " " + symbole
        elif format == "pourcent":
            texte = "{:,.1f}".format(float(valeur)) + " %"
        elif format == "heures":
            heures = int(valeur)
            minutes = int(round((float(valeur) - heures) * 60))
            if minutes == 60:
                heures, minutes = heures + 1, 0
            return "{:,}".format(heures).replace(",", "\u00a0") + "h%02d" % minutes
        else:
            return str(valeur)
    except (ValueError, TypeError):
        return str(valeur)
    return texte.replace(",", "\u00a0").replace(".", ",")


def Evolution(n, n1):
    """ Renvoie l'évolution en % entre n1 et n (ou None si non calculable) """
    if n is None or n1 is None:
        return None
    try:
        n, n1 = float(n), float(n1)
    except (ValueError, TypeError):
        return None
    if n1 == 0:
        return None
    return (n - n1) / abs(n1) * 100.0


def Format_evolution(n, n1, format_valeur="entier"):
    """ Texte court d'évolution pour tableaux : +6,1 % ou +0,8 pt pour les pourcentages """
    if n is None or n1 is None:
        return "-"
    if format_valeur == "pourcent":
        ecart = float(n) - float(n1)
        return ("+" if ecart > 0 else "") + Format_nombre(ecart, "decimal") + " pt"
    evol = Evolution(n, n1)
    if evol is None:
        return "-"
    return ("+" if evol > 0 else "") + Format_nombre(evol, "pourcent")


def Pct(partie, total):
    try:
        return float(partie) / float(total) * 100.0 if total else 0.0
    except (ValueError, TypeError):
        return 0.0


def Pluriel(nbre, singulier, pluriel=None):
    if pluriel is None:
        pluriel = singulier + "s"
    return singulier if abs(nbre or 0) < 2 else pluriel


# ------------------------------------------------------------------------------------------------------
# Constructeurs de blocs
# ------------------------------------------------------------------------------------------------------

def Kpi(label="", valeur=0, n1=None, format="entier", inverse=False, detail=None):
    """ inverse=True : une hausse est défavorable (impayés, absentéisme...) """
    return {"label": label, "valeur": valeur, "n1": n1, "format": format, "inverse": inverse, "detail": detail}

def Bloc_kpis(items=[], colonnes=3):
    return {"type": "kpis", "items": [item for item in items if item], "colonnes": colonnes}

def Bloc_analyse(phrases=[]):
    phrases = [phrase for phrase in phrases if phrase]
    return {"type": "analyse", "phrases": phrases} if phrases else None

def Bloc_tableau(titre="", colonnes=[], lignes=[], formats=None, total=None, note=None, largeurs=None):
    return {"type": "tableau", "titre": titre, "colonnes": colonnes, "lignes": lignes, "formats": formats or [], "total": total, "note": note, "largeurs": largeurs}

def Bloc_barres(titre="", labels=[], series=[], horizontal=False, format="entier"):
    """ series : liste de dict {"nom", "valeurs", "role" ("principal" ou "comparaison")} """
    return {"type": "barres", "titre": titre, "labels": [str(l) for l in labels], "series": series, "horizontal": horizontal, "format": format}

def Bloc_courbe(titre="", labels=[], series=[], format="entier"):
    return {"type": "courbe", "titre": titre, "labels": [str(l) for l in labels], "series": series, "format": format}

def Bloc_camembert(titre="", labels=[], valeurs=[], format="entier"):
    return {"type": "camembert", "titre": titre, "labels": [str(l) for l in labels], "valeurs": [float(v or 0) for v in valeurs], "format": format}

def Bloc_sous_titre(texte=""):
    return {"type": "sous_titre", "texte": texte}

def Bloc_note(texte=""):
    return {"type": "note", "texte": texte}

def Serie(nom="", valeurs=[], role="principal"):
    return {"nom": nom, "valeurs": [float(v or 0) for v in valeurs], "role": role}


class Rubrique():
    def __init__(self, code="", titre=""):
        self.code = code
        self.titre = titre
        self.blocs = []

    def Add(self, bloc=None):
        if bloc:
            self.blocs.append(bloc)

    def Est_vide(self):
        return not any(bloc["type"] not in ("note", "sous_titre") for bloc in self.blocs)


# ------------------------------------------------------------------------------------------------------
# Moteur
# ------------------------------------------------------------------------------------------------------

class Rapport():
    def __init__(self, date_debut=None, date_fin=None, activites=[], toutes_activites=False, etats=("reservation", "present"),
                 rubriques=[], comparer=True, annexes=False, analyses=True, tranches_qf=None, label_periode=None, label_periode_n1=None,
                 symbole_monnaie="€"):
        self.d1, self.d2 = date_debut, date_fin
        self.comparer = comparer
        self.analyses = analyses
        self.annexes = annexes
        self.symbole = symbole_monnaie
        self.toutes_activites = toutes_activites
        self.activites = list(activites)
        self.ids_activites = [activite.pk for activite in self.activites]
        self.dict_activites = {activite.pk: activite.nom for activite in self.activites}
        self.etats = list(etats) or ["reservation", "present"]
        self.rubriques_demandees = rubriques
        self.tranches_qf = self.Parse_tranches_qf(tranches_qf or TRANCHES_QF_DEFAUT)
        self.faits = []
        self.cache = {}

        # Période de comparaison : même période décalée d'un an (ou de la durée de la période si elle dépasse un an)
        nbre_jours = (self.d2 - self.d1).days + 1
        if nbre_jours <= 366:
            self.p1, self.p2 = self.d1 - relativedelta(years=1), self.d2 - relativedelta(years=1)
        else:
            self.p1, self.p2 = self.d1 - datetime.timedelta(days=nbre_jours), self.d1 - datetime.timedelta(days=1)
        self.label_n = label_periode or "la période"
        self.label_n1 = label_periode_n1 or "la période précédente"

        # Liste des mois de la période
        self.mois = []
        date = datetime.date(self.d1.year, self.d1.month, 1)
        while date <= self.d2:
            self.mois.append((date.year, date.month))
            date += relativedelta(months=1)
        self.mois_n1 = []
        for annee, mois in self.mois:
            date = datetime.date(annee, mois, 1) - relativedelta(years=1) if nbre_jours <= 366 else datetime.date(annee, mois, 1) - relativedelta(days=nbre_jours)
            self.mois_n1.append((date.year, date.month))
        multi_annees = len(set(annee for annee, mois in self.mois)) > 1
        self.labels_mois = ["%s %s" % (MOIS_COURTS[m - 1], str(a)[2:]) if multi_annees else MOIS_COURTS[m - 1] for a, m in self.mois]

        # Périodes de vacances
        self.vacances = list(Vacance.objects.filter(date_fin__gte=min(self.p1, self.d1), date_debut__lte=self.d2).values_list("date_debut", "date_fin"))

    # ---------------------------------------------- Utilitaires ----------------------------------------------

    def Parse_tranches_qf(self, texte=""):
        tranches = []
        try:
            for tranche in texte.replace(" ", "").split(";"):
                if "-" in tranche:
                    mini, maxi = tranche.split("-")
                    tranches.append((int(mini), int(maxi)))
        except ValueError:
            tranches = []
        return tranches or self.Parse_tranches_qf(TRANCHES_QF_DEFAUT)

    def Periode(self, n1=False):
        return (self.p1, self.p2) if n1 else (self.d1, self.d2)

    def Est_vacances(self, date):
        for debut, fin in self.vacances:
            if debut <= date <= fin:
                return True
        return False

    def Q_activites(self, champ="activite", inclure_sans_activite=False):
        """ Condition sur les activités sélectionnées """
        condition = Q(**{"%s_id__in" % champ: self.ids_activites})
        if inclure_sans_activite and self.toutes_activites:
            condition |= Q(**{"%s__isnull" % champ: True})
        return condition

    def Conso(self, n1=False, etats=None):
        """ Queryset des consommations de la période """
        d1, d2 = self.Periode(n1)
        return Consommation.objects.filter(activite_id__in=self.ids_activites, date__range=(d1, d2), etat__in=etats or self.etats)

    def Individus_presents(self, n1=False):
        cle = "individus_presents_%s" % n1
        if cle not in self.cache:
            self.cache[cle] = set(self.Conso(n1).values_list("individu_id", flat=True).distinct())
        return self.cache[cle]

    def Familles_presentes(self, n1=False):
        cle = "familles_presentes_%s" % n1
        if cle not in self.cache:
            self.cache[cle] = set(self.Conso(n1).values_list("inscription__famille_id", flat=True).distinct()) - {None}
        return self.cache[cle]

    def Inscriptions(self, n1=False):
        """ Inscriptions actives sur la période """
        d1, d2 = self.Periode(n1)
        return Inscription.objects.filter(activite_id__in=self.ids_activites, date_debut__lte=d2).filter(Q(date_fin__isnull=True) | Q(date_fin__gte=d1))

    def Prestations(self, n1=False):
        d1, d2 = self.Periode(n1)
        return Prestation.objects.filter(self.Q_activites(inclure_sans_activite=True), date__range=(d1, d2))

    def Factures(self, n1=False):
        d1, d2 = self.Periode(n1)
        factures = Facture.objects.filter(date_edition__range=(d1, d2)).exclude(etat="annulation")
        if not self.toutes_activites:
            factures = factures.filter(prestation__activite_id__in=self.ids_activites).distinct()
        return factures

    def Reglements(self, n1=False):
        d1, d2 = self.Periode(n1)
        reglements = Reglement.objects.filter(date__range=(d1, d2))
        if not self.toutes_activites:
            reglements = reglements.filter(Q(famille_id__in=self.Familles_scope()))
        return reglements

    def Familles_scope(self):
        """ Familles inscrites sur les activités sélectionnées (pour filtrer les données financières) """
        if "familles_scope" not in self.cache:
            self.cache["familles_scope"] = set(Inscription.objects.filter(activite_id__in=self.ids_activites).values_list("famille_id", flat=True).distinct())
        return self.cache["familles_scope"]

    def Par_mois(self, dict_dates={}, n1=False):
        """ Convertit un dict {date: valeur} en liste de valeurs par mois de la période """
        mois = self.mois_n1 if n1 else self.mois
        resultats = {cle: 0 for cle in mois}
        for date, valeur in dict_dates.items():
            if hasattr(date, "year"):
                cle = (date.year, date.month)
                if cle in resultats:
                    resultats[cle] += float(valeur or 0)
        return [resultats[cle] for cle in mois]

    def Somme(self, queryset, champ="montant"):
        return queryset.aggregate(total=Sum(champ))["total"] or Decimal(0)

    def Phrase_evol(self, n, n1, format="entier", masculin=True):
        """ Ex : en hausse de 6,1 % par rapport à 2024 (17 389) """
        if not self.comparer or n1 is None:
            return ""
        if format == "pourcent":
            ecart = float(n or 0) - float(n1 or 0)
            if abs(ecart) < 0.05:
                return "stable par rapport à %s" % self.label_n1
            return "%s de %s point%s par rapport à %s (%s)" % ("en hausse" if ecart > 0 else "en baisse", Format_nombre(abs(ecart), "decimal"),
                                                            "s" if abs(ecart) >= 2 else "", self.label_n1, Format_nombre(n1, "pourcent"))
        evol = Evolution(n, n1)
        if evol is None:
            if not n1 and n:
                return "alors qu'aucune donnée n'était enregistrée sur %s" % self.label_n1
            return ""
        if abs(evol) < 1:
            return "%s par rapport à %s (%s)" % ("stable" if masculin else "stable", self.label_n1, Format_nombre(n1, format, self.symbole))
        return "%s de %s par rapport à %s (%s)" % ("en hausse" if evol > 0 else "en baisse", Format_nombre(abs(evol), "pourcent"),
                                                  self.label_n1, Format_nombre(n1, format, self.symbole))

    def Phrase_principale(self, items=[], total=0, unite="", format="entier"):
        """ Ex : L'accueil périscolaire concentre 45,2 % des consommations, devant ... """
        items = [item for item in items if item[1]]
        if not items or not total:
            return ""
        texte = "« %s » arrive en tête avec %s %s (%s du total)" % (items[0][0], Format_nombre(items[0][1], format, self.symbole), unite, Format_nombre(Pct(items[0][1], total), "pourcent"))
        if len(items) > 1:
            texte += ", devant « %s » (%s)" % (items[1][0], Format_nombre(Pct(items[1][1], total), "pourcent"))
        if len(items) > 2:
            texte += " et « %s » (%s)" % (items[2][0], Format_nombre(Pct(items[2][1], total), "pourcent"))
        return texte.replace("  ", " ") + "."

    def Fait(self, texte="", priorite=5):
        """ Fait marquant pour la synthèse """
        if texte:
            self.faits.append((priorite, texte))

    def Kpi_comparatif(self, label, fonction, format="entier", inverse=False, detail=None):
        valeur = fonction(False)
        n1 = fonction(True) if self.comparer else None
        return Kpi(label, valeur, n1, format, inverse, detail)

    def Lignes_comparatives(self, dict_n={}, dict_n1={}, format="entier", total=None, limite=None):
        """ Construit des lignes [label, N, (N-1, évol,) part] triées par valeur décroissante """
        total = total if total is not None else sum(float(v or 0) for v in dict_n.values())
        cles = sorted(set(dict_n.keys()) | (set(dict_n1.keys()) if self.comparer else set()), key=lambda c: -float(dict_n.get(c, 0) or 0))
        lignes = []
        for cle in cles:
            valeur = dict_n.get(cle, 0)
            ligne = [cle if cle not in (None, "") else "Non renseigné", valeur]
            if self.comparer:
                valeur_n1 = dict_n1.get(cle, 0)
                ligne += [valeur_n1, Format_evolution(valeur, valeur_n1, format) if valeur_n1 else "-"]
            ligne.append(Format_nombre(Pct(valeur, total), "pourcent"))
            lignes.append(ligne)
        if limite and len(lignes) > limite:
            autres = lignes[limite:]
            lignes = lignes[:limite]
            valeur = sum(float(l[1] or 0) for l in autres)
            ligne = ["Autres (%d)" % len(autres), valeur]
            if self.comparer:
                valeur_n1 = sum(float(l[2] or 0) for l in autres)
                ligne += [valeur_n1, Format_evolution(valeur, valeur_n1, format) if valeur_n1 else "-"]
            ligne.append(Format_nombre(Pct(valeur, total), "pourcent"))
            lignes.append(ligne)
        return lignes

    def Colonnes_comparatives(self, label="", label_valeur="Nombre", format="entier"):
        colonnes = [label, label_valeur]
        formats = ["texte", format]
        if self.comparer:
            colonnes += [self.Label_court(n1=True), "Évol."]
            formats += [format, "texte"]
        colonnes.append("Part")
        formats.append("texte")
        return colonnes, formats

    def Label_court(self, n1=False):
        label = self.label_n1 if n1 else self.label_n
        return label[0].upper() + label[1:] if not label[0].isdigit() and len(label) < 14 else (label if len(label) < 14 else ("N-1" if n1 else "N"))

    def Total_comparatif(self, lignes=[], format="entier"):
        total = ["Total", sum(float(l[1] or 0) for l in lignes)]
        if self.comparer:
            total_n1 = sum(float(l[2] or 0) for l in lignes)
            total += [total_n1, Format_evolution(total[1], total_n1, format) if total_n1 else "-"]
        total.append("100,0 %")
        return total

    def Series_mensuelles(self, dict_n={}, dict_n1={}, nom=""):
        series = [Serie(self.Label_court() if self.comparer else nom, self.Par_mois(dict_n), "principal")]
        if self.comparer:
            series.insert(0, Serie(self.Label_court(n1=True), self.Par_mois(dict_n1, n1=True), "comparaison"))
        return series

    def Top(self, dict_valeurs={}, limite=6, label_autres="Autres"):
        """ Top N pour camemberts """
        items = sorted([(k if k not in (None, "") else "Non renseigné", float(v or 0)) for k, v in dict_valeurs.items() if v], key=lambda x: -x[1])
        if len(items) > limite:
            autres = sum(v for k, v in items[limite - 1:])
            items = items[:limite - 1] + [(label_autres, autres)]
        return [k for k, v in items], [v for k, v in items]

    # ---------------------------------------------- Lancement ----------------------------------------------

    def Generer(self):
        """ Calcule toutes les rubriques demandées et renvoie la liste des rubriques """
        rubriques = []
        self.rubriques_vides = []
        for code, titre, description in RUBRIQUES:
            if code == "synthese" or code not in self.rubriques_demandees:
                continue
            rubrique = Rubrique(code, titre)
            try:
                getattr(self, "Rubrique_%s" % code)(rubrique)
            except Exception as err:
                logger.exception("Rapport d'activité : erreur dans la rubrique %s" % code)
                rubrique.blocs = [Bloc_note("Cette rubrique n'a pas pu être calculée : %s" % err)]
            # Les rubriques sans donnée ne sont pas imprimées : elles sont signalées dans la synthèse
            if rubrique.Est_vide() and not rubrique.blocs:
                self.rubriques_vides.append(titre)
                continue
            self.Ordonner_blocs(rubrique)
            rubriques.append(rubrique)

        # La synthèse est calculée en dernier pour récupérer les faits marquants des autres rubriques
        if "synthese" in self.rubriques_demandees:
            rubrique = Rubrique("synthese", "Synthèse et chiffres clés")
            try:
                self.Rubrique_synthese(rubrique)
            except Exception as err:
                logger.exception("Rapport d'activité : erreur dans la synthèse")
                rubrique.blocs = [Bloc_note("La synthèse n'a pas pu être calculée : %s" % err)]
            self.Ordonner_blocs(rubrique)
            rubriques.insert(0, rubrique)

        # Si aucune rubrique ne contient de données, on les affiche quand même avec un message
        if not rubriques and self.rubriques_vides:
            for titre in self.rubriques_vides:
                rubrique = Rubrique("vide", titre)
                rubrique.Add(Bloc_note("Aucune donnée n'est disponible pour cette rubrique sur la période sélectionnée."))
                rubriques.append(rubrique)

        # Annexes
        if self.annexes:
            rubrique = Rubrique("annexes", "Annexes")
            try:
                self.Rubrique_annexes(rubrique)
            except Exception as err:
                logger.exception("Rapport d'activité : erreur dans les annexes")
                rubrique.blocs = [Bloc_note("Les annexes n'ont pas pu être calculées : %s" % err)]
            rubriques.append(rubrique)

        return rubriques

    def Ordonner_blocs(self, rubrique):
        """ Place l'analyse juste après les premiers chiffres clés, pour une lecture plus directe """
        analyses = [bloc for bloc in rubrique.blocs if bloc["type"] == "analyse"]
        if not analyses:
            return
        blocs = [bloc for bloc in rubrique.blocs if bloc["type"] != "analyse"]
        position = next((index + 1 for index, bloc in enumerate(blocs) if bloc["type"] == "kpis"), 0)
        rubrique.blocs = blocs[:position] + analyses + blocs[position:]

    # ======================================================================================================
    # SYNTHESE
    # ======================================================================================================

    def Rubrique_synthese(self, rubrique):
        nbre_individus = lambda n1: len(self.Individus_presents(n1))
        nbre_familles = lambda n1: len(self.Familles_presentes(n1))
        nbre_inscriptions = lambda n1: self.Inscriptions(n1).filter(statut="ok").count()
        nbre_conso = lambda n1: self.Conso(n1).count()
        nbre_jours = lambda n1: self.Conso(n1).values("date").distinct().count()

        def taux_absenteisme(n1):
            resultats = dict(self.Conso(n1, etats=("present", "absentj", "absenti")).values_list("etat").annotate(nbre=Count("idconso")))
            total = sum(resultats.values())
            return Pct(resultats.get("absentj", 0) + resultats.get("absenti", 0), total) if total else None

        montant_prestations = lambda n1: self.Somme(self.Prestations(n1))
        montant_facture = lambda n1: self.Somme(self.Factures(n1), "total")
        montant_encaisse = lambda n1: self.Somme(self.Reglements(n1))
        impayes = lambda n1: self.Somme(self.Factures(n1).filter(solde_actuel__gt=0), "solde_actuel")

        kpis = [
            self.Kpi_comparatif("Individus accueillis", nbre_individus),
            self.Kpi_comparatif("Familles", nbre_familles),
            self.Kpi_comparatif("Inscriptions actives", nbre_inscriptions),
            self.Kpi_comparatif("Consommations", nbre_conso),
            self.Kpi_comparatif("Jours d'activité", nbre_jours),
            self.Kpi_comparatif("Taux d'absentéisme", taux_absenteisme, format="pourcent", inverse=True),
            self.Kpi_comparatif("Prestations", montant_prestations, format="montant"),
            self.Kpi_comparatif("Montant facturé", montant_facture, format="montant"),
            self.Kpi_comparatif("Montant encaissé", montant_encaisse, format="montant"),
        ]
        rubrique.Add(Bloc_kpis(kpis, colonnes=3))

        # Analyse générale
        k = {kpi["label"]: kpi for kpi in kpis}
        phrases = []
        texte = "Sur %s, %s %s ont été accueillis, issus de %s %s" % (
            self.label_n, Format_nombre(k["Individus accueillis"]["valeur"]), Pluriel(k["Individus accueillis"]["valeur"], "individu"),
            Format_nombre(k["Familles"]["valeur"]), Pluriel(k["Familles"]["valeur"], "famille"))
        evol = self.Phrase_evol(k["Individus accueillis"]["valeur"], k["Individus accueillis"]["n1"])
        phrases.append(texte + (" (nombre d'individus %s)" % evol if evol else "") + ".")
        if k["Consommations"]["valeur"]:
            texte = "L'activité représente %s consommations réparties sur %s jours" % (Format_nombre(k["Consommations"]["valeur"]), Format_nombre(k["Jours d'activité"]["valeur"]))
            if k["Jours d'activité"]["valeur"]:
                texte += ", soit une moyenne de %s consommations par jour d'activité" % Format_nombre(k["Consommations"]["valeur"] / k["Jours d'activité"]["valeur"], "decimal")
            evol = self.Phrase_evol(k["Consommations"]["valeur"], k["Consommations"]["n1"], masculin=False)
            phrases.append(texte + (" ; la fréquentation est %s" % evol if evol else "") + ".")
        if k["Montant facturé"]["valeur"]:
            texte = "Le montant facturé s'élève à %s" % Format_nombre(k["Montant facturé"]["valeur"], "montant", self.symbole)
            if k["Montant encaissé"]["valeur"]:
                texte += " et le montant encaissé à %s" % Format_nombre(k["Montant encaissé"]["valeur"], "montant", self.symbole)
            reste = impayes(False)
            if reste:
                texte += ". Le reste à recouvrer sur les factures de la période est de %s (%s du facturé)" % (Format_nombre(reste, "montant", self.symbole), Format_nombre(Pct(reste, k["Montant facturé"]["valeur"]), "pourcent"))
            phrases.append(texte + ".")
        if self.analyses:
            rubrique.Add(Bloc_analyse(phrases))

        # Faits marquants
        faits = list(self.faits)
        for kpi in kpis:
            evol = Evolution(kpi["valeur"], kpi["n1"]) if kpi["format"] != "pourcent" else None
            if evol is not None and abs(evol) >= 10 and self.comparer:
                faits.append((3, "%s : %s de %s par rapport à %s." % (kpi["label"], "hausse" if evol > 0 else "baisse", Format_nombre(abs(evol), "pourcent"), self.label_n1)))
        faits = [texte for priorite, texte in sorted(faits, key=operator.itemgetter(0))]
        vus, faits_uniques = set(), []
        for texte in faits:
            if texte not in vus:
                vus.add(texte)
                faits_uniques.append(texte)
        if faits_uniques and self.analyses:
            rubrique.Add(Bloc_sous_titre("Faits marquants"))
            rubrique.Add({"type": "puces", "items": faits_uniques[:8]})

        # Graphique : évolution mensuelle des consommations
        if k["Consommations"]["valeur"]:
            dict_n = dict(self.Conso().values_list("date").annotate(nbre=Count("idconso")))
            dict_n1 = dict(self.Conso(n1=True).values_list("date").annotate(nbre=Count("idconso"))) if self.comparer else {}
            rubrique.Add(Bloc_barres("Évolution mensuelle des consommations", self.labels_mois, self.Series_mensuelles(dict_n, dict_n1, "Consommations")))

        # Tableau récapitulatif
        lignes = []
        for kpi in kpis + [self.Kpi_comparatif("Reste à recouvrer", impayes, format="montant", inverse=True)]:
            ligne = [kpi["label"], Format_nombre(kpi["valeur"], kpi["format"], self.symbole)]
            if self.comparer:
                ligne += [Format_nombre(kpi["n1"], kpi["format"], self.symbole), Format_evolution(kpi["valeur"], kpi["n1"], kpi["format"])]
            lignes.append(ligne)
        colonnes = ["Indicateur", self.Label_court()] + ([self.Label_court(n1=True), "Évol."] if self.comparer else [])
        rubrique.Add(Bloc_tableau("Tableau récapitulatif", colonnes, lignes, ["texte"] * len(colonnes)))
        if getattr(self, "rubriques_vides", None):
            rubrique.Add(Bloc_note("Rubriques non imprimées faute de données sur la période : %s." % ", ".join(self.rubriques_vides)))
        if not self.toutes_activites:
            rubrique.Add(Bloc_note("Les données financières sont limitées aux factures comportant des prestations des activités sélectionnées et aux règlements des familles inscrites à ces activités."))

    # ======================================================================================================
    # ACTIVITES ET OFFRE
    # ======================================================================================================

    def Rubrique_activites(self, rubrique):
        d1, d2 = self.Periode()

        # Activités ayant fonctionné
        conso_par_activite = dict(self.Conso().values_list("activite_id").annotate(nbre=Count("idconso")))
        jours_par_activite = dict(self.Conso().values_list("activite_id").annotate(nbre=Count("date", distinct=True)))
        jours_par_activite_n1 = dict(self.Conso(n1=True).values_list("activite_id").annotate(nbre=Count("date", distinct=True))) if self.comparer else {}
        ouvertures = dict(Ouverture.objects.filter(activite_id__in=self.ids_activites, date__range=(d1, d2)).values_list("activite_id").annotate(nbre=Count("date", distinct=True)))
        groupes = dict(Groupe.objects.filter(activite_id__in=self.ids_activites).values_list("activite_id").annotate(nbre=Count("idgroupe")))
        individus = dict(self.Conso().values_list("activite_id").annotate(nbre=Count("individu_id", distinct=True)))
        activites_actives = [idactivite for idactivite in self.ids_activites if conso_par_activite.get(idactivite)]
        activites_actives_n1 = [idactivite for idactivite in self.ids_activites if jours_par_activite_n1.get(idactivite)]

        # Calcul des taux de remplissage
        taux_par_activite, saturations = self.Calcul_remplissage(d1, d2)

        rubrique.Add(Bloc_kpis([
            Kpi("Activités ayant fonctionné", len(activites_actives), len(activites_actives_n1) if self.comparer else None),
            Kpi("Jours d'activité", self.Conso().values("date").distinct().count(), self.Conso(n1=True).values("date").distinct().count() if self.comparer else None),
            Kpi("Taux de remplissage moyen", taux_par_activite.get("global"), None, "pourcent", detail="sur les capacités paramétrées") if taux_par_activite.get("global") is not None else None,
        ]))

        # Tableau par activité
        lignes = []
        for idactivite in sorted(activites_actives, key=lambda i: -conso_par_activite.get(i, 0)):
            ligne = [self.dict_activites.get(idactivite, "?"), groupes.get(idactivite, 0), ouvertures.get(idactivite) or "-", jours_par_activite.get(idactivite, 0)]
            if self.comparer:
                ligne.append(jours_par_activite_n1.get(idactivite, 0))
            ligne += [individus.get(idactivite, 0), conso_par_activite.get(idactivite, 0), Format_nombre(conso_par_activite.get(idactivite, 0) / jours_par_activite[idactivite], "decimal") if jours_par_activite.get(idactivite) else "-"]
            ligne.append(Format_nombre(taux_par_activite[idactivite], "pourcent") if taux_par_activite.get(idactivite) is not None else "-")
            lignes.append(ligne)
        colonnes = ["Activité", "Groupes", "Jours ouverts", "Jours d'activité"] + ([self.Label_court(n1=True)] if self.comparer else []) + ["Individus", "Conso.", "Conso./jour", "Remplissage"]
        formats = ["texte", "entier", "entier", "entier"] + (["entier"] if self.comparer else []) + ["entier", "entier", "texte", "texte"]
        rubrique.Add(Bloc_tableau("Fonctionnement par activité", colonnes, lignes, formats,
                                  note="Jours ouverts : jours d'ouverture paramétrés au calendrier. Jours d'activité : jours ayant au moins une consommation."))

        # Graphique jours d'activité
        if lignes:
            labels = [ligne[0] for ligne in lignes[:NBRE_MAX_LIGNES]]
            series = [Serie(self.Label_court(), [jours_par_activite.get(i, 0) for i in sorted(activites_actives, key=lambda i: -conso_par_activite.get(i, 0))[:NBRE_MAX_LIGNES]])]
            rubrique.Add(Bloc_barres("Jours d'activité par activité", labels, series, horizontal=True))

        # Analyse
        phrases = []
        if activites_actives:
            phrases.append("%d %s %s fonctionné sur %s%s." % (len(activites_actives), Pluriel(len(activites_actives), "activité"), "a" if len(activites_actives) < 2 else "ont",
                                                            self.label_n, (" (%d sur %s)" % (len(activites_actives_n1), self.label_n1)) if self.comparer and len(activites_actives_n1) != len(activites_actives) else ""))
            idmax = max(activites_actives, key=lambda i: jours_par_activite.get(i, 0))
            phrases.append("L'activité la plus régulière est « %s » avec %d jours d'activité." % (self.dict_activites.get(idmax), jours_par_activite.get(idmax, 0)))
        if taux_par_activite.get("global") is not None:
            texte = "Le taux de remplissage moyen, calculé sur les capacités paramétrées, atteint %s" % Format_nombre(taux_par_activite["global"], "pourcent")
            if saturations:
                texte += ". %d %s ont atteint ou dépassé la capacité maximale" % (saturations, Pluriel(saturations, "journée"))
                self.Fait("%d journées complètes (capacité maximale atteinte)." % saturations, 6)
            phrases.append(texte + ".")
        elif activites_actives:
            phrases.append("Aucune capacité d'accueil n'étant paramétrée, le taux de remplissage ne peut pas être calculé.")
        if self.analyses:
            rubrique.Add(Bloc_analyse(phrases))

    def Calcul_remplissage(self, d1, d2):
        """ Taux de remplissage = individus présents / places paramétrées, pour chaque date, unité de remplissage et groupe """
        remplissages = list(Remplissage.objects.filter(activite_id__in=self.ids_activites, date__range=(d1, d2), places__gt=0).values_list("activite_id", "unite_remplissage_id", "groupe_id", "date", "places"))
        if not remplissages:
            return {}, 0
        unites_remplissage = defaultdict(set)
        for idunite_remplissage, idunite in UniteRemplissage.unites.through.objects.filter(uniteremplissage__activite_id__in=self.ids_activites).values_list("uniteremplissage_id", "unite_id"):
            unites_remplissage[idunite_remplissage].add(idunite)
        # Individus par (date, unité, groupe)
        presents = defaultdict(set)
        for date, idunite, idgroupe, idindividu in self.Conso().values_list("date", "unite_id", "groupe_id", "individu_id"):
            presents[(date, idunite, idgroupe)].add(idindividu)
            presents[(date, idunite, None)].add(idindividu)
        places_par_activite, occupes_par_activite = defaultdict(int), defaultdict(int)
        saturations = 0
        for idactivite, idunite_remplissage, idgroupe, date, places in remplissages:
            individus = set()
            for idunite in unites_remplissage.get(idunite_remplissage, []):
                individus |= presents.get((date, idunite, idgroupe), set())
            # On ne compte que les jours avec de l'activité
            if not individus:
                continue
            places_par_activite[idactivite] += places
            occupes_par_activite[idactivite] += len(individus)
            if len(individus) >= places:
                saturations += 1
        resultats = {idactivite: Pct(occupes_par_activite[idactivite], places_par_activite[idactivite]) for idactivite in places_par_activite}
        if places_par_activite:
            resultats["global"] = Pct(sum(occupes_par_activite.values()), sum(places_par_activite.values()))
        return resultats, saturations

    # ======================================================================================================
    # INSCRIPTIONS
    # ======================================================================================================

    def Rubrique_inscriptions(self, rubrique):
        d1, d2 = self.Periode()
        p1, p2 = self.Periode(n1=True)
        inscriptions = self.Inscriptions().filter(statut="ok")
        inscriptions_n1 = self.Inscriptions(n1=True).filter(statut="ok")
        nouvelles = Inscription.objects.filter(activite_id__in=self.ids_activites, date_debut__range=(d1, d2), statut="ok")
        nouvelles_n1 = Inscription.objects.filter(activite_id__in=self.ids_activites, date_debut__range=(p1, p2), statut="ok")
        nbre, nbre_n1 = inscriptions.count(), inscriptions_n1.count() if self.comparer else None
        nbre_individus = inscriptions.values("individu_id").distinct().count()
        nbre_nouvelles = nouvelles.count()

        # Taux de transformation : inscrits ayant au moins une consommation
        inscrits = set(inscriptions.values_list("individu_id", flat=True))
        presents = self.Individus_presents() & inscrits
        taux_presence = Pct(len(presents), len(inscrits)) if inscrits else None

        rubrique.Add(Bloc_kpis([
            Kpi("Inscriptions actives", nbre, nbre_n1),
            Kpi("Nouvelles inscriptions", nbre_nouvelles, nouvelles_n1.count() if self.comparer else None),
            Kpi("Individus inscrits", nbre_individus, inscriptions_n1.values("individu_id").distinct().count() if self.comparer else None),
            Kpi("Inscrits venus au moins une fois", taux_presence, None, "pourcent") if taux_presence is not None else None,
            Kpi("En attente", self.Inscriptions().filter(statut="attente").count(), None, inverse=True),
            Kpi("Refusées", self.Inscriptions().filter(statut="refus").count(), None, inverse=True),
        ]))

        # Par activité
        dict_n = dict(inscriptions.values_list("activite__nom").annotate(nbre=Count("idinscription")))
        dict_n1 = dict(inscriptions_n1.values_list("activite__nom").annotate(nbre=Count("idinscription"))) if self.comparer else {}
        lignes = self.Lignes_comparatives(dict_n, dict_n1)
        colonnes, formats = self.Colonnes_comparatives("Activité", "Inscriptions")
        rubrique.Add(Bloc_tableau("Inscriptions actives par activité", colonnes, lignes, formats, total=self.Total_comparatif(lignes) if len(lignes) > 1 else None))

        # Par groupe
        dict_groupes = {"%s - %s" % (activite, groupe): nbre for activite, groupe, nbre in inscriptions.values_list("activite__nom", "groupe__nom").annotate(nbre=Count("idinscription"))}
        if len(dict_groupes) > 1:
            labels, valeurs = self.Top(dict_groupes, limite=NBRE_MAX_LIGNES)
            rubrique.Add(Bloc_barres("Inscriptions par groupe", labels, [Serie("Inscriptions", valeurs)], horizontal=True))

        # Par catégorie de tarif
        dict_categories = {"%s - %s" % (activite, categorie): nbre for activite, categorie, nbre in inscriptions.values_list("activite__nom", "categorie_tarif__nom").annotate(nbre=Count("idinscription"))}
        if len(dict_categories) > 1:
            lignes = [[label, nbre, Format_nombre(Pct(nbre, sum(dict_categories.values())), "pourcent")] for label, nbre in sorted(dict_categories.items(), key=lambda x: -x[1])]
            rubrique.Add(Bloc_tableau("Inscriptions par catégorie de tarif", ["Activité - Catégorie", "Inscriptions", "Part"], lignes, ["texte", "entier", "texte"]))

        # Evolution mensuelle des nouvelles inscriptions
        dict_n = dict(nouvelles.values_list("date_debut").annotate(nbre=Count("idinscription")))
        dict_n1 = dict(nouvelles_n1.values_list("date_debut").annotate(nbre=Count("idinscription"))) if self.comparer else {}
        if dict_n:
            rubrique.Add(Bloc_barres("Nouvelles inscriptions par mois (date de début)", self.labels_mois, self.Series_mensuelles(dict_n, dict_n1, "Nouvelles inscriptions")))

        # Multi-inscriptions
        compteur = Counter(Counter(inscriptions.values_list("individu_id", flat=True)).values())
        if compteur and max(compteur) > 1:
            labels = ["%d %s" % (nbre, Pluriel(nbre, "inscription")) for nbre in sorted(compteur)]
            rubrique.Add(Bloc_camembert("Nombre d'inscriptions par individu", labels, [compteur[nbre] for nbre in sorted(compteur)]))

        # Analyse
        phrases = []
        if nbre:
            texte = "%s inscriptions étaient actives sur %s" % (Format_nombre(nbre), self.label_n)
            evol = self.Phrase_evol(nbre, nbre_n1, masculin=False)
            phrases.append(texte + (", %s" % evol if evol else "") + ", pour %s %s." % (Format_nombre(nbre_individus), Pluriel(nbre_individus, "individu")))
            phrases.append("%s nouvelles inscriptions ont débuté au cours de la période (%s des inscriptions actives)." % (Format_nombre(nbre_nouvelles), Format_nombre(Pct(nbre_nouvelles, nbre), "pourcent")))
            phrases.append(self.Phrase_principale(sorted(dict(inscriptions.values_list("activite__nom").annotate(nbre=Count("idinscription"))).items(), key=lambda x: -x[1]), nbre, "inscriptions"))
            if taux_presence is not None:
                texte = "%s des individus inscrits sont venus au moins une fois" % Format_nombre(taux_presence, "pourcent")
                if taux_presence < 80:
                    texte += " : %s inscrits n'ont aucune consommation sur la période, ce qui peut révéler des inscriptions à mettre à jour" % Format_nombre(len(inscrits) - len(presents))
                phrases.append(texte + ".")
            multi = sum(v for k, v in compteur.items() if k > 1)
            if multi:
                phrases.append("%s individus (%s) sont inscrits à plusieurs activités." % (Format_nombre(multi), Format_nombre(Pct(multi, nbre_individus), "pourcent")))
            evol = Evolution(nbre_nouvelles, nouvelles_n1.count()) if self.comparer else None
            if evol is not None and abs(evol) >= 10:
                self.Fait("Nouvelles inscriptions en %s de %s." % ("hausse" if evol > 0 else "baisse", Format_nombre(abs(evol), "pourcent")), 4)
        if self.analyses:
            rubrique.Add(Bloc_analyse(phrases))

    # ======================================================================================================
    # PUBLIC ACCUEILLI
    # ======================================================================================================

    def Rubrique_public(self, rubrique):
        d1, d2 = self.Periode()
        ids = self.Individus_presents()
        ids_n1 = self.Individus_presents(n1=True) if self.comparer else set()
        if not ids:
            return

        # Nouveaux individus : aucune consommation avant le début de la période sur les activités
        anciens = set(Consommation.objects.filter(activite_id__in=self.ids_activites, date__lt=d1, individu_id__in=ids, etat__in=self.etats).values_list("individu_id", flat=True).distinct())
        nouveaux = len(ids - anciens)

        # Données individuelles (champs chiffrés : agrégation en python)
        individus = list(Individu.objects.filter(pk__in=ids).values_list("idindividu", "civilite", "date_naiss", "ville_resid", "secteur__nom"))
        individus_n1 = list(Individu.objects.filter(pk__in=ids_n1).values_list("idindividu", "civilite", "date_naiss")) if ids_n1 else []

        def genre(civilite):
            if civilite in (1, 4): return "Masculin"
            if civilite in (2, 3, 5): return "Féminin"
            return "Non renseigné"

        def age(date_naiss, reference):
            if not date_naiss: return None
            return reference.year - date_naiss.year - ((reference.month, reference.day) < (date_naiss.month, date_naiss.day))

        def tranche(valeur):
            if valeur is None: return "Non renseigné"
            for mini, maxi, label in TRANCHES_AGES:
                if mini <= valeur <= maxi: return label
            return "Non renseigné"

        genres = Counter(genre(i[1]) for i in individus)
        ages = [age(i[2], d1) for i in individus]
        ages_connus = [a for a in ages if a is not None and 0 <= a < 120]
        tranches = Counter(tranche(a) for a in ages)
        tranches_n1 = Counter(tranche(age(i[2], self.p1)) for i in individus_n1)
        villes = Counter((i[3] or "").strip().upper() or "Non renseignée" for i in individus)
        secteurs = Counter(i[4] or "Non renseigné" for i in individus)
        age_moyen = sum(ages_connus) / len(ages_connus) if ages_connus else None

        rubrique.Add(Bloc_kpis([
            Kpi("Individus accueillis", len(ids), len(ids_n1) if self.comparer else None),
            Kpi("Nouveaux individus", nouveaux, None, detail="%s du public" % Format_nombre(Pct(nouveaux, len(ids)), "pourcent")),
            Kpi("Âge moyen", age_moyen, None, "decimal", detail="au début de la période") if age_moyen is not None else None,
        ]))

        # Genre
        rubrique.Add(Bloc_sous_titre("Genre"))
        labels = [g for g in ("Masculin", "Féminin", "Non renseigné") if genres.get(g)]
        rubrique.Add(Bloc_camembert("Répartition par genre", labels, [genres[g] for g in labels]))

        # Ages
        rubrique.Add(Bloc_sous_titre("Âges"))
        labels = [label for mini, maxi, label in TRANCHES_AGES if tranches.get(label) or tranches_n1.get(label)]
        if tranches.get("Non renseigné"):
            labels.append("Non renseigné")
        series = [Serie(self.Label_court() if self.comparer else "Individus", [tranches.get(l, 0) for l in labels])]
        if self.comparer and individus_n1:
            series.insert(0, Serie(self.Label_court(n1=True), [tranches_n1.get(l, 0) for l in labels], "comparaison"))
        rubrique.Add(Bloc_barres("Répartition par tranche d'âge", labels, series))
        detail_ages = Counter(a for a in ages_connus)
        if detail_ages:
            lignes = [["%d %s" % (a, Pluriel(a, "an")), detail_ages[a], Format_nombre(Pct(detail_ages[a], len(ids)), "pourcent")] for a in sorted(detail_ages)]
            rubrique.Add(Bloc_tableau("Détail par âge", ["Âge", "Individus", "Part"], lignes, ["texte", "entier", "texte"]))

        # Lieu de résidence
        rubrique.Add(Bloc_sous_titre("Lieu de résidence"))
        lignes = self.Lignes_simples(villes, len(ids), limite=NBRE_MAX_LIGNES)
        rubrique.Add(Bloc_tableau("Répartition par ville de résidence", ["Ville", "Individus", "Part"], lignes, ["texte", "entier", "texte"]))
        if len(secteurs) > 1 or "Non renseigné" not in secteurs:
            labels, valeurs = self.Top(secteurs, limite=7)
            rubrique.Add(Bloc_camembert("Répartition par secteur", labels, valeurs))

        # Scolarité
        scolarites = {}
        for idindividu, ecole, niveau in Scolarite.objects.filter(individu_id__in=ids, date_debut__lte=d2, date_fin__gte=d1).order_by("date_debut").values_list("individu_id", "ecole__nom", "niveau__nom"):
            scolarites[idindividu] = (ecole, niveau)
        if scolarites:
            rubrique.Add(Bloc_sous_titre("Scolarité"))
            ecoles = Counter(s[0] or "Non renseignée" for s in scolarites.values())
            niveaux = Counter(s[1] or "Non renseigné" for s in scolarites.values())
            rubrique.Add(Bloc_tableau("Répartition par école", ["École", "Individus", "Part"], self.Lignes_simples(ecoles, len(scolarites), limite=NBRE_MAX_LIGNES), ["texte", "entier", "texte"]))
            labels, valeurs = self.Top(niveaux, limite=NBRE_MAX_LIGNES)
            rubrique.Add(Bloc_barres("Répartition par niveau scolaire", labels, [Serie("Individus", valeurs)], horizontal=True))
            rubrique.Add(Bloc_note("%s individus scolarisés renseignés sur %s accueillis." % (Format_nombre(len(scolarites)), Format_nombre(len(ids)))))

        # Analyse
        phrases = []
        texte = "%s individus ont fréquenté les activités" % Format_nombre(len(ids))
        evol = self.Phrase_evol(len(ids), len(ids_n1) if self.comparer else None)
        phrases.append(texte + (", %s" % evol if evol else "") + ". Parmi eux, %s sont de nouveaux usagers (%s)." % (Format_nombre(nouveaux), Format_nombre(Pct(nouveaux, len(ids)), "pourcent")))
        if genres.get("Masculin") or genres.get("Féminin"):
            phrases.append("Le public se compose de %s de garçons/hommes et %s de filles/femmes." % (Format_nombre(Pct(genres.get("Masculin", 0), len(ids)), "pourcent"), Format_nombre(Pct(genres.get("Féminin", 0), len(ids)), "pourcent")))
        if ages_connus:
            tranche_max = max([(l, n) for l, n in tranches.items() if l != "Non renseigné"] or [("", 0)], key=lambda x: x[1])
            texte = "L'âge moyen est de %s ans" % Format_nombre(age_moyen, "decimal")
            if tranche_max[1]:
                texte += " ; la tranche la plus représentée est celle des %s (%s)" % (tranche_max[0], Format_nombre(Pct(tranche_max[1], len(ids)), "pourcent"))
            phrases.append(texte + ".")
            if tranches.get("Non renseigné"):
                phrases.append("La date de naissance n'est pas renseignée pour %s individus." % Format_nombre(tranches["Non renseigné"]))
        ville_max = max([(v, n) for v, n in villes.items() if v != "Non renseignée"] or [("", 0)], key=lambda x: x[1])
        if ville_max[1]:
            phrases.append("%s des individus résident à %s ; %d %s de résidence différentes sont représentées." % (Format_nombre(Pct(ville_max[1], len(ids)), "pourcent"), ville_max[0].title(), len(villes), Pluriel(len(villes), "commune")))
        if self.analyses:
            rubrique.Add(Bloc_analyse(phrases))
        if nouveaux and Pct(nouveaux, len(ids)) >= 25:
            self.Fait("%s nouveaux usagers accueillis (%s du public)." % (Format_nombre(nouveaux), Format_nombre(Pct(nouveaux, len(ids)), "pourcent")), 5)

    def Lignes_simples(self, compteur={}, total=0, limite=None):
        items = sorted(compteur.items(), key=lambda x: (-x[1], str(x[0])))
        lignes = [[label, nbre, Format_nombre(Pct(nbre, total), "pourcent")] for label, nbre in items]
        if limite and len(lignes) > limite:
            autres = lignes[limite:]
            lignes = lignes[:limite]
            nbre = sum(l[1] for l in autres)
            lignes.append(["Autres (%d)" % len(autres), nbre, Format_nombre(Pct(nbre, total), "pourcent")])
        return lignes

    # ======================================================================================================
    # FAMILLES
    # ======================================================================================================

    def Rubrique_familles(self, rubrique):
        d1, d2 = self.Periode()
        p1, p2 = self.Periode(n1=True)
        ids = self.Familles_presentes()
        ids_n1 = self.Familles_presentes(n1=True) if self.comparer else set()
        if not ids:
            return
        familles = list(Famille.objects.filter(pk__in=ids).values_list("idfamille", "date_creation", "caisse__nom", "caisse__regime__nom", "secteur__nom", "internet_actif"))
        nouvelles = sum(1 for f in familles if f[1] and d1 <= f[1].date() <= d2)

        # Composition : nombre d'individus accueillis par famille
        compo = Counter(Counter(famille for individu, famille in set(self.Conso().values_list("individu_id", "inscription__famille_id"))).values())
        nbre_moyen = sum(k * v for k, v in compo.items()) / sum(compo.values()) if compo else 0

        rubrique.Add(Bloc_kpis([
            Kpi("Familles accueillies", len(ids), len(ids_n1) if self.comparer else None),
            Kpi("Nouvelles familles", nouvelles, sum(1 for d in Famille.objects.filter(pk__in=ids_n1).values_list("date_creation", flat=True) if d and p1 <= d.date() <= p2) if self.comparer else None),
            Kpi("Individus accueillis par famille", nbre_moyen, None, "decimal"),
        ]))

        # Composition
        labels = ["%d %s" % (k, Pluriel(k, "individu")) for k in sorted(compo)]
        rubrique.Add(Bloc_camembert("Nombre d'individus accueillis par famille", labels, [compo[k] for k in sorted(compo)]))

        # Quotients familiaux
        quotients = {}
        for idfamille, quotient in Quotient.objects.filter(famille_id__in=ids, date_debut__lte=d2, date_fin__gte=d1).order_by("date_debut").values_list("famille_id", "quotient"):
            if quotient is not None:
                quotients[idfamille] = float(quotient)
        rubrique.Add(Bloc_sous_titre("Quotients familiaux"))
        if quotients:
            compteur = Counter()
            for valeur in quotients.values():
                label = "Hors tranches"
                for mini, maxi in self.tranches_qf:
                    if mini <= valeur <= maxi:
                        label = "%s à %s" % (Format_nombre(mini), Format_nombre(maxi)) if maxi < 99999 else "%s et +" % Format_nombre(mini)
                        break
                compteur[label] += 1
            ordre = [("%s à %s" % (Format_nombre(mini), Format_nombre(maxi)) if maxi < 99999 else "%s et +" % Format_nombre(mini)) for mini, maxi in self.tranches_qf] + ["Hors tranches"]
            labels = [l for l in ordre if compteur.get(l)]
            sans_qf = len(ids) - len(quotients)
            if sans_qf:
                labels.append("QF non renseigné")
                compteur["QF non renseigné"] = sans_qf
            rubrique.Add(Bloc_barres("Répartition des familles par tranche de QF", labels, [Serie("Familles", [compteur[l] for l in labels])]))
            liste = sorted(quotients.values())
            mediane = liste[len(liste) // 2] if len(liste) % 2 else (liste[len(liste) // 2 - 1] + liste[len(liste) // 2]) / 2
            rubrique.Add(Bloc_kpis([Kpi("QF moyen", sum(liste) / len(liste), None, "entier"), Kpi("QF médian", mediane, None, "entier"),
                                    Kpi("Familles avec QF", len(quotients), None, detail="%s des familles" % Format_nombre(Pct(len(quotients), len(ids)), "pourcent"))]))
        else:
            rubrique.Add(Bloc_note("Aucun quotient familial n'est renseigné pour les familles accueillies sur la période."))

        # Caisses et régimes
        rubrique.Add(Bloc_sous_titre("Caisses et régimes"))
        caisses = Counter(f[2] or "Non renseignée" for f in familles)
        regimes = Counter(f[3] or "Non renseigné" for f in familles)
        rubrique.Add(Bloc_tableau("Répartition par caisse", ["Caisse", "Familles", "Part"], self.Lignes_simples(caisses, len(ids), limite=NBRE_MAX_LIGNES), ["texte", "entier", "texte"]))
        labels, valeurs = self.Top(regimes, limite=6)
        rubrique.Add(Bloc_camembert("Répartition par régime social", labels, valeurs))

        # Secteurs
        secteurs = Counter(f[4] or "Non renseigné" for f in familles)
        if len(secteurs) > 1 or "Non renseigné" not in secteurs:
            rubrique.Add(Bloc_tableau("Répartition par secteur", ["Secteur", "Familles", "Part"], self.Lignes_simples(secteurs, len(ids), limite=NBRE_MAX_LIGNES), ["texte", "entier", "texte"]))

        # Ancienneté
        anciennete = Counter()
        for f in familles:
            if not f[1]:
                anciennete["Non renseignée"] += 1
                continue
            annees = (d2 - f[1].date()).days // 365
            label = "Moins d'1 an" if annees < 1 else ("1 à 2 ans" if annees < 3 else ("3 à 5 ans" if annees < 6 else ("6 à 10 ans" if annees < 11 else "Plus de 10 ans")))
            anciennete[label] += 1
        ordre = [l for l in ("Moins d'1 an", "1 à 2 ans", "3 à 5 ans", "6 à 10 ans", "Plus de 10 ans", "Non renseignée") if anciennete.get(l)]
        rubrique.Add(Bloc_barres("Ancienneté des familles (date de création du dossier)", ordre, [Serie("Familles", [anciennete[l] for l in ordre])]))

        # Analyse
        phrases = []
        evol = self.Phrase_evol(len(ids), len(ids_n1) if self.comparer else None, masculin=False)
        phrases.append("%s familles ont bénéficié des activités%s, dont %s nouvelles familles (dossier créé sur la période)." % (Format_nombre(len(ids)), (", %s" % evol) if evol else "", Format_nombre(nouvelles)))
        if compo:
            phrases.append("Chaque famille compte en moyenne %s individus accueillis ; %s des familles n'ont qu'un seul individu accueilli." % (Format_nombre(nbre_moyen, "decimal"), Format_nombre(Pct(compo.get(1, 0), len(ids)), "pourcent")))
        if quotients:
            phrases.append("Le quotient familial moyen s'établit à %s (médiane : %s). Il est renseigné pour %s des familles." % (Format_nombre(sum(quotients.values()) / len(quotients)), Format_nombre(mediane), Format_nombre(Pct(len(quotients), len(ids)), "pourcent")))
        caisse_max = max([(c, n) for c, n in caisses.items() if c != "Non renseignée"] or [("", 0)], key=lambda x: x[1])
        if caisse_max[1]:
            phrases.append("La caisse la plus représentée est %s (%s des familles)." % (caisse_max[0], Format_nombre(Pct(caisse_max[1], len(ids)), "pourcent")))
        if self.analyses:
            rubrique.Add(Bloc_analyse(phrases))

    # ======================================================================================================
    # FREQUENTATION
    # ======================================================================================================

    def Rubrique_frequentation(self, rubrique):
        conso = self.Conso()
        par_date = dict(conso.values_list("date").annotate(nbre=Count("idconso")))
        if not par_date:
            return
        par_date_n1 = dict(self.Conso(n1=True).values_list("date").annotate(nbre=Count("idconso"))) if self.comparer else {}
        total, total_n1 = sum(par_date.values()), sum(par_date_n1.values()) if self.comparer else None
        nbre_jours, nbre_jours_n1 = len(par_date), len(par_date_n1)
        moyenne = total / nbre_jours
        date_pic = max(par_date, key=par_date.get)

        # Equivalents journées et heures
        equiv_journees = 0.0
        for equiv, nbre in conso.values_list("unite__equiv_journees").annotate(nbre=Count("idconso")):
            equiv_journees += float(equiv or 0) * nbre
        heures = 0.0
        for debut, fin in conso.filter(heure_debut__isnull=False, heure_fin__isnull=False).values_list("heure_debut", "heure_fin"):
            duree = (datetime.datetime.combine(datetime.date.today(), fin) - datetime.datetime.combine(datetime.date.today(), debut)).total_seconds() / 3600
            if duree > 0:
                heures += duree

        # Vacances
        total_vacances = sum(nbre for date, nbre in par_date.items() if self.Est_vacances(date))

        rubrique.Add(Bloc_kpis([
            Kpi("Consommations", total, total_n1),
            Kpi("Moyenne par jour d'activité", moyenne, total_n1 / nbre_jours_n1 if self.comparer and nbre_jours_n1 else None, "decimal"),
            Kpi("Pic journalier", par_date[date_pic], None, detail="le %s" % date_pic.strftime("%d/%m/%Y")),
            Kpi("Part vacances scolaires", Pct(total_vacances, total), None, "pourcent", detail="%s conso." % Format_nombre(total_vacances)) if self.vacances else None,
            Kpi("Équivalent journées", equiv_journees, None, "decimal") if equiv_journees else None,
            Kpi("Heures de présence", heures, None, "heures") if heures else None,
        ]))

        # Par mois
        rubrique.Add(Bloc_barres("Consommations par mois", self.labels_mois, self.Series_mensuelles(par_date, par_date_n1, "Consommations")))

        # Par jour de semaine
        jours = Counter()
        for date, nbre in par_date.items():
            jours[date.weekday()] += nbre
        jours_n1 = Counter()
        for date, nbre in par_date_n1.items():
            jours_n1[date.weekday()] += nbre
        index_jours = [i for i in range(7) if jours.get(i) or jours_n1.get(i)]
        series = [Serie(self.Label_court() if self.comparer else "Consommations", [jours.get(i, 0) for i in index_jours])]
        if self.comparer and par_date_n1:
            series.insert(0, Serie(self.Label_court(n1=True), [jours_n1.get(i, 0) for i in index_jours], "comparaison"))
        rubrique.Add(Bloc_barres("Consommations par jour de la semaine", [JOURS[i] for i in index_jours], series))

        # Par activité
        dict_n = dict(conso.values_list("activite__nom").annotate(nbre=Count("idconso")))
        dict_n1 = dict(self.Conso(n1=True).values_list("activite__nom").annotate(nbre=Count("idconso"))) if self.comparer else {}
        lignes = self.Lignes_comparatives(dict_n, dict_n1, total=total)
        colonnes, formats = self.Colonnes_comparatives("Activité", "Conso.")
        rubrique.Add(Bloc_tableau("Consommations par activité", colonnes, lignes, formats, total=self.Total_comparatif(lignes) if len(lignes) > 1 else None))

        # Par unité
        dict_unites = {"%s - %s" % (activite, unite): nbre for activite, unite, nbre in conso.values_list("activite__nom", "unite__nom").annotate(nbre=Count("idconso"))}
        if len(dict_unites) > 1:
            labels, valeurs = self.Top(dict_unites, limite=7)
            rubrique.Add(Bloc_camembert("Répartition par unité de consommation", labels, valeurs))
            lignes = self.Lignes_simples(dict_unites, total, limite=NBRE_MAX_LIGNES * 2)
            rubrique.Add(Bloc_tableau("Consommations par unité", ["Activité - Unité", "Conso.", "Part"], lignes, ["texte", "entier", "texte"]))

        # Par groupe
        dict_groupes = {"%s - %s" % (activite, groupe): nbre for activite, groupe, nbre in conso.values_list("activite__nom", "groupe__nom").annotate(nbre=Count("idconso"))}
        if len(dict_groupes) > 1:
            labels, valeurs = self.Top(dict_groupes, limite=NBRE_MAX_LIGNES)
            rubrique.Add(Bloc_barres("Consommations par groupe", labels, [Serie("Conso.", valeurs)], horizontal=True))

        # Etats (tous états confondus)
        etats = dict(Consommation.objects.filter(activite_id__in=self.ids_activites, date__range=self.Periode()).values_list("etat").annotate(nbre=Count("idconso")))
        if len(etats) > 1:
            labels = [ETATS_LABELS.get(e, e) for e in etats]
            rubrique.Add(Bloc_camembert("Consommations par état (tous états confondus)", labels, list(etats.values())))

        # Top 10 des journées
        top = sorted(par_date.items(), key=lambda x: -x[1])[:10]
        lignes = [["%s %s" % (JOURS[d.weekday()], d.strftime("%d/%m/%Y")), n, "Oui" if self.Est_vacances(d) else "Non"] for d, n in top]
        rubrique.Add(Bloc_tableau("Les 10 journées les plus fréquentées", ["Date", "Conso.", "Vacances"], lignes, ["texte", "entier", "texte"]))

        # Analyse
        phrases = []
        evol = self.Phrase_evol(total, total_n1, masculin=False)
        phrases.append("%s consommations ont été enregistrées sur %s jours d'activité%s." % (Format_nombre(total), Format_nombre(nbre_jours), (" ; la fréquentation est %s" % evol) if evol else ""))
        phrases.append("La moyenne s'établit à %s consommations par jour d'activité, avec un pic de %s le %s %s." % (Format_nombre(moyenne, "decimal"), Format_nombre(par_date[date_pic]), JOURS[date_pic.weekday()].lower(), date_pic.strftime("%d/%m/%Y")))
        mois_valeurs = self.Par_mois(par_date)
        if len([v for v in mois_valeurs if v]) > 1:
            index_max = mois_valeurs.index(max(mois_valeurs))
            mois_actifs = [(v, i) for i, v in enumerate(mois_valeurs) if v]
            index_min = min(mois_actifs)[1]
            phrases.append("Le mois le plus chargé est %s %d (%s consommations) et le moins chargé %s %d (%s)." % (
                MOIS_LONGS[self.mois[index_max][1] - 1], self.mois[index_max][0], Format_nombre(mois_valeurs[index_max]),
                MOIS_LONGS[self.mois[index_min][1] - 1], self.mois[index_min][0], Format_nombre(mois_valeurs[index_min])))
            self.Fait("Mois le plus chargé : %s %d (%s consommations)." % (MOIS_LONGS[self.mois[index_max][1] - 1], self.mois[index_max][0], Format_nombre(mois_valeurs[index_max])), 4)
        if jours:
            jour_max = max(jours, key=jours.get)
            phrases.append("Le %s est le jour le plus fréquenté (%s des consommations)." % (JOURS[jour_max].lower(), Format_nombre(Pct(jours[jour_max], total), "pourcent")))
        if self.vacances:
            phrases.append("Les vacances scolaires représentent %s de l'activité." % Format_nombre(Pct(total_vacances, total), "pourcent"))
        items = sorted(dict_n.items(), key=lambda x: -x[1])
        phrases.append(self.Phrase_principale(items, total, "consommations"))
        if self.comparer:
            evolutions = [(nom, Evolution(n, dict_n1.get(nom))) for nom, n in dict_n.items() if dict_n1.get(nom, 0) >= 50]
            evolutions = [e for e in evolutions if e[1] is not None]
            if evolutions:
                hausse = max(evolutions, key=lambda x: x[1])
                baisse = min(evolutions, key=lambda x: x[1])
                if hausse[1] >= 5:
                    phrases.append("La plus forte progression concerne « %s » (+%s)." % (hausse[0], Format_nombre(hausse[1], "pourcent")))
                    self.Fait("Fréquentation de « %s » en hausse de %s." % (hausse[0], Format_nombre(hausse[1], "pourcent")), 2)
                if baisse[1] <= -5:
                    phrases.append("La baisse la plus marquée concerne « %s » (%s)." % (baisse[0], Format_nombre(baisse[1], "pourcent")))
                    self.Fait("Fréquentation de « %s » en baisse de %s." % (baisse[0], Format_nombre(abs(baisse[1]), "pourcent")), 2)
        if self.analyses:
            rubrique.Add(Bloc_analyse(phrases))

    # ======================================================================================================
    # ABSENCES
    # ======================================================================================================

    def Rubrique_absences(self, rubrique):
        etats = ("present", "absentj", "absenti")
        conso = self.Conso(etats=etats)
        conso_n1 = self.Conso(n1=True, etats=etats)
        resultats = dict(conso.values_list("etat").annotate(nbre=Count("idconso")))
        total = sum(resultats.values())
        if not total:
            rubrique.Add(Bloc_note("Aucun pointage (présent ou absent) n'a été effectué sur la période : l'absentéisme ne peut pas être calculé."))
            return
        resultats_n1 = dict(conso_n1.values_list("etat").annotate(nbre=Count("idconso"))) if self.comparer else {}
        total_n1 = sum(resultats_n1.values())
        aj, ai = resultats.get("absentj", 0), resultats.get("absenti", 0)
        taux = Pct(aj + ai, total)
        taux_n1 = Pct(resultats_n1.get("absentj", 0) + resultats_n1.get("absenti", 0), total_n1) if total_n1 else None

        # Individus avec absences injustifiées répétées
        recidivistes = sum(1 for nbre in Counter(conso.filter(etat="absenti").values_list("individu_id", flat=True)).values() if nbre >= 3)

        rubrique.Add(Bloc_kpis([
            Kpi("Taux d'absentéisme", taux, taux_n1, "pourcent", inverse=True),
            Kpi("Absences justifiées", aj, resultats_n1.get("absentj") if self.comparer else None, inverse=True),
            Kpi("Absences injustifiées", ai, resultats_n1.get("absenti") if self.comparer else None, inverse=True),
            Kpi("Taux d'absences injustifiées", Pct(ai, total), Pct(resultats_n1.get("absenti", 0), total_n1) if total_n1 else None, "pourcent", inverse=True),
            Kpi("Individus avec 3 absences injustifiées ou +", recidivistes, None, inverse=True),
        ]))

        rubrique.Add(Bloc_camembert("Répartition des pointages", ["Présent", "Absence justifiée", "Absence injustifiée"], [resultats.get("present", 0), aj, ai]))

        # Par activité
        lignes = []
        par_activite = defaultdict(Counter)
        for activite, etat, nbre in conso.values_list("activite__nom", "etat").annotate(nbre=Count("idconso")):
            par_activite[activite][etat] = nbre
        par_activite_n1 = defaultdict(Counter)
        for activite, etat, nbre in conso_n1.values_list("activite__nom", "etat").annotate(nbre=Count("idconso")):
            par_activite_n1[activite][etat] = nbre
        for activite, compteur in sorted(par_activite.items(), key=lambda x: -sum(x[1].values())):
            t = sum(compteur.values())
            ligne = [activite, compteur.get("present", 0), compteur.get("absentj", 0), compteur.get("absenti", 0), Format_nombre(Pct(compteur.get("absentj", 0) + compteur.get("absenti", 0), t), "pourcent")]
            if self.comparer:
                c1 = par_activite_n1.get(activite)
                ligne.append(Format_nombre(Pct(c1.get("absentj", 0) + c1.get("absenti", 0), sum(c1.values())), "pourcent") if c1 else "-")
            lignes.append(ligne)
        colonnes = ["Activité", "Présents", "Abs. justifiées", "Abs. injustifiées", "Taux"] + (["Taux " + self.Label_court(n1=True)] if self.comparer else [])
        rubrique.Add(Bloc_tableau("Absentéisme par activité", colonnes, lignes, ["texte", "entier", "entier", "entier", "texte", "texte"]))

        # Taux mensuel
        par_mois_total, par_mois_abs = defaultdict(int), defaultdict(int)
        for date, etat, nbre in conso.values_list("date", "etat").annotate(nbre=Count("idconso")):
            par_mois_total[date] += nbre
            if etat != "present":
                par_mois_abs[date] += nbre
        totaux, absences = self.Par_mois(par_mois_total), self.Par_mois(par_mois_abs)
        series = [Serie(self.Label_court() if self.comparer else "Taux", [Pct(a, t) for a, t in zip(absences, totaux)])]
        if self.comparer and total_n1:
            par_mois_total_n1, par_mois_abs_n1 = defaultdict(int), defaultdict(int)
            for date, etat, nbre in conso_n1.values_list("date", "etat").annotate(nbre=Count("idconso")):
                par_mois_total_n1[date] += nbre
                if etat != "present":
                    par_mois_abs_n1[date] += nbre
            totaux_n1, absences_n1 = self.Par_mois(par_mois_total_n1, n1=True), self.Par_mois(par_mois_abs_n1, n1=True)
            series.insert(0, Serie(self.Label_court(n1=True), [Pct(a, t) for a, t in zip(absences_n1, totaux_n1)], "comparaison"))
        rubrique.Add(Bloc_courbe("Taux d'absentéisme mensuel (%)", self.labels_mois, series, format="pourcent"))

        # Par jour de semaine
        jours_total, jours_abs = Counter(), Counter()
        for date, etat, nbre in conso.values_list("date", "etat").annotate(nbre=Count("idconso")):
            jours_total[date.weekday()] += nbre
            if etat != "present":
                jours_abs[date.weekday()] += nbre
        index_jours = [i for i in range(7) if jours_total.get(i)]
        rubrique.Add(Bloc_barres("Taux d'absentéisme par jour de la semaine (%)", [JOURS[i] for i in index_jours], [Serie("Taux", [Pct(jours_abs[i], jours_total[i]) for i in index_jours])], format="pourcent"))

        # Analyse
        phrases = []
        evol = self.Phrase_evol(taux, taux_n1, "pourcent")
        phrases.append("Sur %s consommations pointées, %s absences ont été relevées, soit un taux d'absentéisme de %s%s." % (Format_nombre(total), Format_nombre(aj + ai), Format_nombre(taux, "pourcent"), (", %s" % evol) if evol else ""))
        if aj + ai:
            phrases.append("%s des absences sont justifiées et %s injustifiées." % (Format_nombre(Pct(aj, aj + ai), "pourcent"), Format_nombre(Pct(ai, aj + ai), "pourcent")))
        if lignes:
            pire = max(par_activite.items(), key=lambda x: Pct(x[1].get("absentj", 0) + x[1].get("absenti", 0), sum(x[1].values())) if sum(x[1].values()) >= 30 else -1)
            t = sum(pire[1].values())
            if t >= 30:
                phrases.append("L'activité la plus touchée est « %s » avec un taux de %s." % (pire[0], Format_nombre(Pct(pire[1].get("absentj", 0) + pire[1].get("absenti", 0), t), "pourcent")))
        if index_jours:
            jour_max = max(index_jours, key=lambda i: Pct(jours_abs[i], jours_total[i]))
            phrases.append("Le %s présente le taux d'absence le plus élevé (%s)." % (JOURS[jour_max].lower(), Format_nombre(Pct(jours_abs[jour_max], jours_total[jour_max]), "pourcent")))
        if recidivistes:
            phrases.append("%s individus cumulent au moins trois absences injustifiées : un suivi auprès de ces familles peut être envisagé." % Format_nombre(recidivistes))
        if taux_n1 is not None and taux - taux_n1 >= 1:
            self.Fait("Absentéisme en hausse : %s (+%s pt)." % (Format_nombre(taux, "pourcent"), Format_nombre(taux - taux_n1, "decimal")), 3)
        if self.analyses:
            rubrique.Add(Bloc_analyse(phrases))
        rubrique.Add(Bloc_note("Le taux d'absentéisme est calculé sur les consommations pointées (présent, absence justifiée, absence injustifiée)."))

    # ======================================================================================================
    # EVENEMENTS
    # ======================================================================================================

    def Rubrique_evenements(self, rubrique):
        d1, d2 = self.Periode()
        evenements = list(Evenement.objects.filter(activite_id__in=self.ids_activites, date__range=(d1, d2)).values_list("idevenement", "nom", "date", "activite__nom", "categorie__nom", "capacite_max", "montant"))
        if not evenements:
            return
        nbre_n1 = Evenement.objects.filter(activite_id__in=self.ids_activites, date__range=self.Periode(n1=True)).count() if self.comparer else None
        participants = dict(self.Conso().filter(evenement__isnull=False).values_list("evenement_id").annotate(nbre=Count("individu_id", distinct=True)))
        total_participants = sum(participants.values())
        avec_capacite = [e for e in evenements if e[5]]
        taux = Pct(sum(participants.get(e[0], 0) for e in avec_capacite), sum(e[5] for e in avec_capacite)) if avec_capacite else None

        rubrique.Add(Bloc_kpis([
            Kpi("Événements organisés", len(evenements), nbre_n1),
            Kpi("Participations", total_participants, None),
            Kpi("Participants par événement", total_participants / len(evenements), None, "decimal"),
            Kpi("Taux de remplissage", taux, None, "pourcent", detail="événements avec capacité") if taux is not None else None,
        ]))

        # Par catégorie
        categories = Counter(e[4] or "Sans catégorie" for e in evenements)
        if len(categories) > 1:
            labels, valeurs = self.Top(categories, limite=7)
            rubrique.Add(Bloc_camembert("Événements par catégorie", labels, valeurs))

        # Par activité
        par_activite = Counter(e[3] for e in evenements)
        part_activite = Counter()
        for e in evenements:
            part_activite[e[3]] += participants.get(e[0], 0)
        lignes = [[a, n, part_activite[a], Format_nombre(part_activite[a] / n, "decimal")] for a, n in par_activite.most_common()]
        rubrique.Add(Bloc_tableau("Événements par activité", ["Activité", "Événements", "Participations", "Moy. / événement"], lignes, ["texte", "entier", "entier", "texte"]))

        # Liste des événements
        lignes = []
        for e in sorted(evenements, key=lambda e: e[2]):
            nbre = participants.get(e[0], 0)
            lignes.append([e[2].strftime("%d/%m/%Y"), e[1], e[3], nbre, e[5] or "-", Format_nombre(Pct(nbre, e[5]), "pourcent") if e[5] else "-"])
        rubrique.Add(Bloc_tableau("Liste des événements", ["Date", "Événement", "Activité", "Participants", "Capacité", "Remplissage"], lignes, ["texte", "texte", "texte", "entier", "entier", "texte"]))

        # Analyse
        phrases = []
        evol = self.Phrase_evol(len(evenements), nbre_n1)
        phrases.append("%d %s %s été %s%s, totalisant %s participations." % (len(evenements), Pluriel(len(evenements), "événement"), "a" if len(evenements) < 2 else "ont",
                                                                          "organisé" if len(evenements) < 2 else "organisés", (" (%s)" % evol) if evol else "", Format_nombre(total_participants)))
        top = max(evenements, key=lambda e: participants.get(e[0], 0))
        if participants.get(top[0]):
            phrases.append("L'événement le plus suivi est « %s » du %s avec %s participants." % (top[1], top[2].strftime("%d/%m/%Y"), Format_nombre(participants[top[0]])))
        if taux is not None:
            complets = sum(1 for e in avec_capacite if participants.get(e[0], 0) >= e[5])
            texte_complets = "aucun n'était complet" if not complets else ("un seul était complet" if complets == 1 else "%d étaient complets" % complets)
            phrases.append("Le taux de remplissage moyen des événements à capacité limitée est de %s ; %s." % (Format_nombre(taux, "pourcent"), texte_complets))
        if self.analyses:
            rubrique.Add(Bloc_analyse(phrases))

    # ======================================================================================================
    # PRESTATIONS
    # ======================================================================================================

    def Rubrique_prestations(self, rubrique):
        prestations = self.Prestations()
        prestations_n1 = self.Prestations(n1=True)
        total = self.Somme(prestations)
        nbre = prestations.count()
        if not nbre:
            return
        total_n1 = self.Somme(prestations_n1) if self.comparer else None
        nbre_familles = prestations.values("famille_id").distinct().count()
        deductions = Deduction.objects.filter(prestation__in=prestations)
        total_deductions = self.Somme(deductions)
        total_aides = self.Somme(deductions.filter(aide__isnull=False))
        total_initial = self.Somme(prestations, "montant_initial")

        rubrique.Add(Bloc_kpis([
            Kpi("Montant des prestations", total, total_n1, "montant"),
            Kpi("Nombre de prestations", nbre, prestations_n1.count() if self.comparer else None),
            Kpi("Montant moyen", total / nbre, (total_n1 / prestations_n1.count()) if self.comparer and prestations_n1.count() else None, "montant"),
            Kpi("Montant moyen par famille", total / nbre_familles if nbre_familles else 0, None, "montant"),
            Kpi("Déductions", total_deductions, None, "montant", detail="dont %s d'aides" % Format_nombre(total_aides, "montant", self.symbole)),
            Kpi("Gratuités (montant nul)", prestations.filter(montant=0).count(), None),
        ]))

        # Par activité
        dict_n = {k or "Hors activité (adhésions, locations...)": v for k, v in prestations.values_list("activite__nom").annotate(total=Sum("montant"))}
        dict_n1 = {k or "Hors activité (adhésions, locations...)": v for k, v in prestations_n1.values_list("activite__nom").annotate(total=Sum("montant"))} if self.comparer else {}
        lignes = self.Lignes_comparatives(dict_n, dict_n1, format="montant", total=total)
        colonnes, formats = self.Colonnes_comparatives("Activité", "Montant", "montant")
        rubrique.Add(Bloc_tableau("Montant des prestations par activité", colonnes, lignes, formats, total=self.Total_comparatif(lignes, "montant") if len(lignes) > 1 else None))

        # Par mois
        par_date = dict(prestations.values_list("date").annotate(total=Sum("montant")))
        par_date_n1 = dict(prestations_n1.values_list("date").annotate(total=Sum("montant"))) if self.comparer else {}
        rubrique.Add(Bloc_barres("Montant des prestations par mois", self.labels_mois, self.Series_mensuelles(par_date, par_date_n1, "Montant"), format="montant"))

        # Par catégorie
        labels_categories = dict(Prestation._meta.get_field("categorie").choices)
        categories = {labels_categories.get(k, k): v for k, v in prestations.values_list("categorie").annotate(total=Sum("montant"))}
        if len(categories) > 1:
            labels, valeurs = self.Top(categories, limite=6)
            rubrique.Add(Bloc_camembert("Répartition par catégorie de prestation", labels, valeurs, format="montant"))

        # Par catégorie de tarif
        tarifs = {"%s - %s" % (a or "Sans activité", c): v for a, c, v in prestations.filter(categorie_tarif__isnull=False).values_list("activite__nom", "categorie_tarif__nom").annotate(total=Sum("montant"))}
        if len(tarifs) > 1:
            lignes = [[label, float(v), Format_nombre(Pct(v, total), "pourcent")] for label, v in sorted(tarifs.items(), key=lambda x: -x[1])]
            rubrique.Add(Bloc_tableau("Montant par catégorie de tarif", ["Activité - Catégorie", "Montant", "Part"], lignes, ["texte", "montant", "texte"]))

        # Principales prestations
        labels = list(prestations.values_list("label").annotate(nbre=Count("idprestation"), total=Sum("montant")).order_by("-total")[:NBRE_MAX_LIGNES])
        lignes = [[label, nb, float(t or 0), Format_nombre(float(t or 0) / nb, "montant", self.symbole) if nb else "-"] for label, nb, t in labels]
        rubrique.Add(Bloc_tableau("Principales prestations (par montant)", ["Prestation", "Nombre", "Montant", "Montant moyen"], lignes, ["texte", "entier", "montant", "texte"]))

        # Déductions et aides
        if total_deductions:
            rubrique.Add(Bloc_sous_titre("Déductions et aides"))
            aides = {"%s%s" % (nom, " (%s)" % caisse if caisse else ""): v for nom, caisse, v in deductions.filter(aide__isnull=False).values_list("aide__nom", "aide__caisse__nom").annotate(total=Sum("montant"))}
            autres = {label: v for label, v in deductions.filter(aide__isnull=True).values_list("label").annotate(total=Sum("montant"))}
            lignes = [[label, float(v), "Aide"] for label, v in sorted(aides.items(), key=lambda x: -x[1])] + \
                     [[label, float(v), "Déduction"] for label, v in sorted(autres.items(), key=lambda x: -x[1])][:NBRE_MAX_LIGNES]
            rubrique.Add(Bloc_tableau("Détail des déductions", ["Libellé", "Montant", "Type"], lignes, ["texte", "montant", "texte"],
                                      total=["Total", float(total_deductions), ""]))

        # Analyse
        phrases = []
        evol = self.Phrase_evol(total, total_n1, "montant")
        phrases.append("Les prestations de la période représentent %s pour %s prestations%s." % (Format_nombre(total, "montant", self.symbole), Format_nombre(nbre), (", un montant %s" % evol) if evol else ""))
        phrases.append(self.Phrase_principale(sorted(dict_n.items(), key=lambda x: -x[1]), total, "", "montant"))
        phrases.append("Le montant moyen s'établit à %s par prestation et à %s par famille." % (Format_nombre(total / nbre, "montant", self.symbole), Format_nombre(total / nbre_familles if nbre_familles else 0, "montant", self.symbole)))
        if total_deductions:
            phrases.append("Les déductions s'élèvent à %s (%s du montant initial), dont %s au titre d'aides." % (Format_nombre(total_deductions, "montant", self.symbole), Format_nombre(Pct(total_deductions, total_initial), "pourcent"), Format_nombre(total_aides, "montant", self.symbole)))
        if self.analyses:
            rubrique.Add(Bloc_analyse(phrases))

    # ======================================================================================================
    # FACTURATION
    # ======================================================================================================

    def Rubrique_facturation(self, rubrique):
        factures = self.Factures()
        valeurs = list(factures.values_list("idfacture", "date_edition", "total", "regle", "solde_actuel", "famille_id", "lot__nom"))
        if not valeurs:
            return
        factures_n1 = self.Factures(n1=True)
        total = sum(float(v[2] or 0) for v in valeurs)
        total_n1 = float(self.Somme(factures_n1, "total")) if self.comparer else None
        nbre_n1 = factures_n1.count() if self.comparer else None
        reste = sum(float(v[4] or 0) for v in valeurs if (v[4] or 0) > 0)
        nbre_annulees = Facture.objects.filter(date_edition__range=self.Periode(), etat="annulation").count()
        nbre_familles = len(set(v[5] for v in valeurs))

        rubrique.Add(Bloc_kpis([
            Kpi("Factures émises", len(valeurs), nbre_n1),
            Kpi("Montant facturé", total, total_n1, "montant"),
            Kpi("Montant moyen", total / len(valeurs), total_n1 / nbre_n1 if self.comparer and nbre_n1 else None, "montant"),
            Kpi("Familles facturées", nbre_familles, None),
            Kpi("Reste dû", reste, None, "montant", inverse=True),
            Kpi("Factures annulées", nbre_annulees, None, inverse=True),
        ]))

        # Par mois
        par_date, par_date_n1 = defaultdict(float), defaultdict(float)
        for v in valeurs:
            par_date[v[1]] += float(v[2] or 0)
        if self.comparer:
            for date, t in factures_n1.values_list("date_edition", "total"):
                par_date_n1[date] += float(t or 0)
        rubrique.Add(Bloc_barres("Montant facturé par mois (date d'édition)", self.labels_mois, self.Series_mensuelles(par_date, par_date_n1, "Montant"), format="montant"))

        # Etat de règlement
        soldees = [v for v in valeurs if (v[4] or 0) <= 0]
        partielles = [v for v in valeurs if (v[4] or 0) > 0 and (v[3] or 0) > 0]
        impayees = [v for v in valeurs if (v[4] or 0) > 0 and not (v[3] or 0)]
        lignes = [[label, len(liste), sum(float(v[2] or 0) for v in liste), sum(float(v[4] or 0) for v in liste if (v[4] or 0) > 0), Format_nombre(Pct(len(liste), len(valeurs)), "pourcent")]
                  for label, liste in (("Soldées", soldees), ("Partiellement réglées", partielles), ("Non réglées", impayees))]
        rubrique.Add(Bloc_tableau("Situation des factures à ce jour", ["Situation", "Factures", "Montant", "Reste dû", "Part"], lignes,
                                  ["texte", "entier", "montant", "montant", "texte"], total=["Total", len(valeurs), total, reste, "100,0 %"]))
        rubrique.Add(Bloc_camembert("Répartition des factures par situation", ["Soldées", "Partiellement réglées", "Non réglées"], [len(soldees), len(partielles), len(impayees)]))

        # Tranches de montants
        tranches = [(0, 50), (50, 100), (100, 200), (200, 500), (500, 1000), (1000, 10 ** 9)]
        compteur = Counter()
        for v in valeurs:
            montant = float(v[2] or 0)
            for mini, maxi in tranches:
                if mini <= montant < maxi:
                    compteur[(mini, maxi)] += 1
                    break
        labels = [("%d à %d %s" % (mini, maxi, self.symbole)) if maxi < 10 ** 9 else ("%d %s et +" % (mini, self.symbole)) for mini, maxi in tranches if compteur.get((mini, maxi))]
        rubrique.Add(Bloc_barres("Répartition des factures par montant", labels, [Serie("Factures", [compteur[t] for t in tranches if compteur.get(t)])]))

        # Par lot
        lots = defaultdict(lambda: [0, 0.0])
        for v in valeurs:
            lots[v[6] or "Hors lot"][0] += 1
            lots[v[6] or "Hors lot"][1] += float(v[2] or 0)
        if len(lots) > 1:
            lignes = [[nom, n, m] for nom, (n, m) in sorted(lots.items(), key=lambda x: str(x[0]))]
            rubrique.Add(Bloc_tableau("Factures par lot", ["Lot", "Factures", "Montant"], lignes, ["texte", "entier", "montant"]))

        # Analyse
        phrases = []
        evol = self.Phrase_evol(total, total_n1, "montant")
        phrases.append("%s factures ont été émises pour un montant total de %s%s, soit %s en moyenne par facture." % (Format_nombre(len(valeurs)), Format_nombre(total, "montant", self.symbole), (" (%s)" % evol) if evol else "", Format_nombre(total / len(valeurs), "montant", self.symbole)))
        phrases.append("À ce jour, %s des factures sont soldées. Le reste dû s'élève à %s, soit %s du montant facturé." % (Format_nombre(Pct(len(soldees), len(valeurs)), "pourcent"), Format_nombre(reste, "montant", self.symbole), Format_nombre(Pct(reste, total), "pourcent")))
        if nbre_annulees:
            phrases.append("%d %s %s été %s sur la période." % (nbre_annulees, Pluriel(nbre_annulees, "facture"), "a" if nbre_annulees < 2 else "ont", "annulée" if nbre_annulees < 2 else "annulées"))
        if self.analyses:
            rubrique.Add(Bloc_analyse(phrases))

    # ======================================================================================================
    # REGLEMENTS
    # ======================================================================================================

    def Rubrique_reglements(self, rubrique):
        reglements = self.Reglements()
        total = float(self.Somme(reglements))
        nbre = reglements.count()
        if not nbre:
            return
        reglements_n1 = self.Reglements(n1=True)
        total_n1 = float(self.Somme(reglements_n1)) if self.comparer else None
        en_ligne = reglements.filter(paiement__isnull=False).distinct()
        total_en_ligne = float(self.Somme(Reglement.objects.filter(pk__in=en_ligne.values("pk"))))
        en_ligne_n1 = reglements_n1.filter(paiement__isnull=False).distinct() if self.comparer else None
        total_en_ligne_n1 = float(self.Somme(Reglement.objects.filter(pk__in=en_ligne_n1.values("pk")))) if self.comparer else None
        en_attente = reglements.filter(encaissement_attente=True).count()

        # Délai moyen de paiement (date règlement - date d'édition de la facture), pondéré par le montant ventilé
        somme_delais, somme_montants = 0.0, 0.0
        for date_reglement, date_facture, montant in Ventilation.objects.filter(reglement__in=reglements, prestation__facture__isnull=False).values_list("reglement__date", "prestation__facture__date_edition", "montant"):
            if date_reglement and date_facture:
                delai = (date_reglement - date_facture).days
                if delai >= 0:
                    somme_delais += delai * float(montant or 0)
                    somme_montants += float(montant or 0)
        delai_moyen = somme_delais / somme_montants if somme_montants else None
        non_ventile = total - float(self.Somme(Ventilation.objects.filter(reglement__in=reglements)))

        rubrique.Add(Bloc_kpis([
            Kpi("Montant encaissé", total, total_n1, "montant"),
            Kpi("Règlements", nbre, reglements_n1.count() if self.comparer else None),
            Kpi("Montant moyen", total / nbre, None, "montant"),
            Kpi("Paiements en ligne", Pct(total_en_ligne, total), Pct(total_en_ligne_n1, total_n1) if self.comparer and total_n1 else None, "pourcent", detail="du montant encaissé"),
            Kpi("Délai moyen de paiement", delai_moyen, None, "decimal", detail="jours après la facture") if delai_moyen is not None else None,
            Kpi("Non ventilé", max(non_ventile, 0), None, "montant", inverse=True),
        ]))

        # Par mode
        modes = {k or "Non renseigné": float(v) for k, v in reglements.values_list("mode__label").annotate(total=Sum("montant"))}
        modes_n1 = {k or "Non renseigné": float(v) for k, v in reglements_n1.values_list("mode__label").annotate(total=Sum("montant"))} if self.comparer else {}
        nbre_modes = {k or "Non renseigné": v for k, v in reglements.values_list("mode__label").annotate(nbre=Count("idreglement"))}
        lignes = self.Lignes_comparatives(modes, modes_n1, "montant", total=total)
        for ligne in lignes:
            ligne.insert(1, nbre_modes.get(ligne[0], 0))
        colonnes, formats = self.Colonnes_comparatives("Mode de règlement", "Montant", "montant")
        colonnes.insert(1, "Nombre")
        formats.insert(1, "entier")
        rubrique.Add(Bloc_tableau("Règlements par mode", colonnes, lignes, formats))
        labels, valeurs = self.Top(modes, limite=7)
        rubrique.Add(Bloc_camembert("Répartition du montant encaissé par mode", labels, valeurs, format="montant"))

        # Par mois
        par_date = dict(reglements.values_list("date").annotate(total=Sum("montant")))
        par_date_n1 = dict(reglements_n1.values_list("date").annotate(total=Sum("montant"))) if self.comparer else {}
        rubrique.Add(Bloc_barres("Montant encaissé par mois", self.labels_mois, self.Series_mensuelles(par_date, par_date_n1, "Montant"), format="montant"))

        # Paiements en ligne
        if total_en_ligne:
            systemes = {k or "Autre": v for k, v in Paiement.objects.filter(reglements__in=en_ligne).values_list("systeme_paiement").annotate(nbre=Count("idpaiement", distinct=True))}
            lignes = [[k.capitalize(), v] for k, v in sorted(systemes.items(), key=lambda x: -x[1])]
            rubrique.Add(Bloc_tableau("Paiements en ligne par système", ["Système", "Paiements"], lignes, ["texte", "entier"]))

        # Emetteurs
        emetteurs = {k: float(v) for k, v in reglements.filter(emetteur__isnull=False).values_list("emetteur__nom").annotate(total=Sum("montant"))}
        if emetteurs:
            rubrique.Add(Bloc_tableau("Principaux émetteurs", ["Émetteur", "Montant", "Part"], [[k, v, Format_nombre(Pct(v, total), "pourcent")] for k, v in sorted(emetteurs.items(), key=lambda x: -x[1])[:NBRE_MAX_LIGNES]], ["texte", "montant", "texte"]))

        # Dépôts
        depots = Depot.objects.filter(date__range=self.Periode())
        if depots.exists():
            rubrique.Add(Bloc_note("%d dépôts en banque ont été réalisés sur la période pour un montant de %s. %d règlements restent en attente d'encaissement." % (depots.count(), Format_nombre(self.Somme(depots), "montant", self.symbole), en_attente)))

        # Analyse
        phrases = []
        evol = self.Phrase_evol(total, total_n1, "montant")
        phrases.append("%s ont été encaissés au travers de %s règlements%s." % (Format_nombre(total, "montant", self.symbole), Format_nombre(nbre), (", un montant %s" % evol) if evol else ""))
        if modes:
            mode_max = max(modes.items(), key=lambda x: x[1])
            phrases.append("Le mode de règlement le plus utilisé est « %s » (%s du montant encaissé)." % (mode_max[0], Format_nombre(Pct(mode_max[1], total), "pourcent")))
        if total_en_ligne:
            texte = "Les paiements en ligne représentent %s du montant encaissé" % Format_nombre(Pct(total_en_ligne, total), "pourcent")
            if self.comparer and total_n1:
                texte += " (contre %s sur %s)" % (Format_nombre(Pct(total_en_ligne_n1, total_n1), "pourcent"), self.label_n1)
                if Pct(total_en_ligne, total) - Pct(total_en_ligne_n1, total_n1) >= 3:
                    self.Fait("Progression des paiements en ligne : %s des encaissements (contre %s)." % (Format_nombre(Pct(total_en_ligne, total), "pourcent"), Format_nombre(Pct(total_en_ligne_n1, total_n1), "pourcent")), 3)
            phrases.append(texte + ".")
        if delai_moyen is not None:
            phrases.append("Les familles règlent en moyenne leurs factures %s jours après leur édition." % Format_nombre(delai_moyen))
        if non_ventile > 1:
            phrases.append("%s de règlements ne sont pas encore ventilés sur des prestations." % Format_nombre(non_ventile, "montant", self.symbole))
        if self.analyses:
            rubrique.Add(Bloc_analyse(phrases))
        if not self.toutes_activites:
            rubrique.Add(Bloc_note("Règlements des familles inscrites aux activités sélectionnées, toutes prestations confondues."))

    # ======================================================================================================
    # RECOUVREMENT
    # ======================================================================================================

    def Rubrique_recouvrement(self, rubrique):
        d1, d2 = self.Periode()
        rappels = Rappel.objects.filter(date_edition__range=(d1, d2))
        if not self.toutes_activites:
            rappels = rappels.filter(famille_id__in=self.Familles_scope())
        nbre_rappels = rappels.count()
        nbre_rappels_n1 = (Rappel.objects.filter(date_edition__range=self.Periode(n1=True)).filter(**({} if self.toutes_activites else {"famille_id__in": self.Familles_scope()})).count()) if self.comparer else None

        # Impayés à ce jour sur toutes les factures émises jusqu'à la fin de la période
        factures = Facture.objects.filter(date_edition__lte=d2, solde_actuel__gt=0).exclude(etat="annulation")
        if not self.toutes_activites:
            factures = factures.filter(prestation__activite_id__in=self.ids_activites).distinct()
        impayes = list(factures.values_list("date_edition", "date_echeance", "solde_actuel", "famille_id"))
        total_impayes = sum(float(v[2] or 0) for v in impayes)
        facture_periode = float(self.Somme(self.Factures(), "total"))
        reste_periode = float(self.Somme(self.Factures().filter(solde_actuel__gt=0), "solde_actuel"))
        taux_recouvrement = Pct(facture_periode - reste_periode, facture_periode) if facture_periode else None

        if not nbre_rappels and not impayes and taux_recouvrement is None:
            return

        rubrique.Add(Bloc_kpis([
            Kpi("Taux de recouvrement", taux_recouvrement, None, "pourcent", detail="factures de la période") if taux_recouvrement is not None else None,
            Kpi("Impayés à ce jour", total_impayes, None, "montant", inverse=True, detail="factures jusqu'au %s" % d2.strftime("%d/%m/%Y")),
            Kpi("Familles concernées", len(set(v[3] for v in impayes)), None, inverse=True),
            Kpi("Factures impayées", len(impayes), None, inverse=True),
            Kpi("Rappels émis", nbre_rappels, nbre_rappels_n1, inverse=True),
            Kpi("Montant des rappels", self.Somme(rappels, "solde"), None, "montant", inverse=True),
        ]))

        # Ancienneté des impayés
        if impayes:
            aujourdhui = datetime.date.today()
            tranches = [(0, 30, "Moins de 30 jours"), (30, 90, "30 à 90 jours"), (90, 180, "3 à 6 mois"), (180, 365, "6 mois à 1 an"), (365, 100000, "Plus d'1 an")]
            montants, nombres = Counter(), Counter()
            for date_edition, date_echeance, solde, famille in impayes:
                reference = date_echeance or date_edition
                jours = (aujourdhui - reference).days if reference else 0
                for mini, maxi, label in tranches:
                    if mini <= jours < maxi or (jours < 0 and mini == 0):
                        montants[label] += float(solde or 0)
                        nombres[label] += 1
                        break
            labels = [label for mini, maxi, label in tranches if nombres.get(label)]
            rubrique.Add(Bloc_tableau("Ancienneté des impayés (depuis l'échéance)", ["Ancienneté", "Factures", "Montant", "Part"],
                                      [[l, nombres[l], montants[l], Format_nombre(Pct(montants[l], total_impayes), "pourcent")] for l in labels],
                                      ["texte", "entier", "montant", "texte"], total=["Total", len(impayes), total_impayes, "100,0 %"]))
            rubrique.Add(Bloc_barres("Montant des impayés par ancienneté", labels, [Serie("Montant", [montants[l] for l in labels])], format="montant"))

            # Répartition des familles par montant dû
            par_famille = defaultdict(float)
            for v in impayes:
                par_famille[v[3]] += float(v[2] or 0)
            tranches_f = [(0, 50), (50, 200), (200, 500), (500, 1000), (1000, 10 ** 9)]
            compteur = Counter()
            for montant in par_famille.values():
                for mini, maxi in tranches_f:
                    if mini <= montant < maxi:
                        compteur[(mini, maxi)] += 1
                        break
            lignes = [[("%d à %d %s" % (mini, maxi, self.symbole)) if maxi < 10 ** 9 else ("%d %s et +" % (mini, self.symbole)), compteur[(mini, maxi)]] for mini, maxi in tranches_f if compteur.get((mini, maxi))]
            rubrique.Add(Bloc_tableau("Familles par montant restant dû", ["Montant dû", "Familles"], lignes, ["texte", "entier"]))

        # Rappels
        if nbre_rappels:
            modeles = {k or "Sans modèle": v for k, v in rappels.values_list("modele__label").annotate(nbre=Count("idrappel"))}
            if len(modeles) > 1:
                labels, valeurs = self.Top(modeles, limite=6)
                rubrique.Add(Bloc_camembert("Rappels par modèle", labels, valeurs))

        # Analyse
        phrases = []
        if taux_recouvrement is not None:
            phrases.append("Le taux de recouvrement des factures émises sur la période atteint %s à ce jour." % Format_nombre(taux_recouvrement, "pourcent"))
        if impayes:
            phrases.append("Le montant total restant dû s'élève à %s, réparti sur %s factures et %s familles." % (Format_nombre(total_impayes, "montant", self.symbole), Format_nombre(len(impayes)), Format_nombre(len(set(v[3] for v in impayes)))))
            anciens = montants.get("6 mois à 1 an", 0) + montants.get("Plus d'1 an", 0)
            if anciens:
                phrases.append("%s des impayés ont plus de six mois (%s) : leur recouvrement devient plus incertain." % (Format_nombre(Pct(anciens, total_impayes), "pourcent"), Format_nombre(anciens, "montant", self.symbole)))
            self.Fait("Reste à recouvrer : %s sur %s familles." % (Format_nombre(total_impayes, "montant", self.symbole), Format_nombre(len(set(v[3] for v in impayes)))), 4)
        if nbre_rappels:
            evol = self.Phrase_evol(nbre_rappels, nbre_rappels_n1)
            phrases.append("%s rappels ont été émis%s." % (Format_nombre(nbre_rappels), (" (%s)" % evol) if evol else ""))
        if self.analyses:
            rubrique.Add(Bloc_analyse(phrases))

    # ======================================================================================================
    # ADHESIONS
    # ======================================================================================================

    def Rubrique_adhesions(self, rubrique):
        d1, d2 = self.Periode()
        p1, p2 = self.Periode(n1=True)

        def valides(n1=False):
            debut, fin = self.Periode(n1)
            cotisations = Cotisation.objects.filter(date_debut__lte=fin, date_fin__gte=debut)
            if not self.toutes_activites:
                cotisations = cotisations.filter(famille_id__in=self.Familles_scope())
            return cotisations

        cotisations = valides()
        nbre = cotisations.count()
        if not nbre:
            return
        cotisations_n1 = valides(n1=True)
        nouvelles = cotisations.filter(date_saisie__date__range=(d1, d2))
        montant = self.Somme(Prestation.objects.filter(cotisation__in=cotisations))
        individuelles = cotisations.filter(individu__isnull=False).count()

        rubrique.Add(Bloc_kpis([
            Kpi("Adhésions valides", nbre, cotisations_n1.count() if self.comparer else None),
            Kpi("Nouvelles adhésions", nouvelles.count(), cotisations_n1.filter(date_saisie__date__range=(p1, p2)).count() if self.comparer else None),
            Kpi("Montant des adhésions", montant, self.Somme(Prestation.objects.filter(cotisation__in=cotisations_n1)) if self.comparer else None, "montant"),
            Kpi("Adhésions individuelles", individuelles, None, detail="%d familiales" % (nbre - individuelles)),
        ]))

        # Par type
        dict_n = dict(cotisations.values_list("type_cotisation__nom").annotate(nbre=Count("idcotisation")))
        dict_n1 = dict(cotisations_n1.values_list("type_cotisation__nom").annotate(nbre=Count("idcotisation"))) if self.comparer else {}
        lignes = self.Lignes_comparatives(dict_n, dict_n1)
        colonnes, formats = self.Colonnes_comparatives("Type d'adhésion", "Adhésions")
        rubrique.Add(Bloc_tableau("Adhésions par type", colonnes, lignes, formats, total=self.Total_comparatif(lignes) if len(lignes) > 1 else None))

        # Par unité
        unites = {"%s - %s" % (t, u): v for t, u, v in cotisations.values_list("type_cotisation__nom", "unite_cotisation__nom").annotate(nbre=Count("idcotisation"))}
        if len(unites) > 1:
            labels, valeurs = self.Top(unites, limite=7)
            rubrique.Add(Bloc_camembert("Adhésions par unité", labels, valeurs))

        # Nouvelles adhésions par mois
        par_date = Counter(d.date() for d in nouvelles.values_list("date_saisie", flat=True) if d)
        if par_date:
            par_date_n1 = Counter(d.date() for d in cotisations_n1.filter(date_saisie__date__range=(p1, p2)).values_list("date_saisie", flat=True) if d) if self.comparer else {}
            rubrique.Add(Bloc_barres("Nouvelles adhésions par mois (date de saisie)", self.labels_mois, self.Series_mensuelles(par_date, par_date_n1, "Adhésions")))

        # Montant par type
        montants = {k: float(v or 0) for k, v in Prestation.objects.filter(cotisation__in=cotisations).values_list("cotisation__type_cotisation__nom").annotate(total=Sum("montant"))}
        if montants:
            rubrique.Add(Bloc_tableau("Montant des adhésions par type", ["Type d'adhésion", "Montant", "Part"], [[k, v, Format_nombre(Pct(v, montant), "pourcent")] for k, v in sorted(montants.items(), key=lambda x: -x[1])], ["texte", "montant", "texte"]))

        # Analyse
        phrases = []
        evol = self.Phrase_evol(nbre, cotisations_n1.count() if self.comparer else None, masculin=False)
        phrases.append("%s adhésions étaient valides sur la période%s, dont %s nouvelles adhésions saisies." % (Format_nombre(nbre), (", %s" % evol) if evol else "", Format_nombre(nouvelles.count())))
        phrases.append(self.Phrase_principale(sorted(dict_n.items(), key=lambda x: -x[1]), nbre, "adhésions"))
        if montant:
            phrases.append("Les adhésions représentent un montant de %s." % Format_nombre(montant, "montant", self.symbole))
        if self.analyses:
            rubrique.Add(Bloc_analyse(phrases))

    # ======================================================================================================
    # LOCATIONS
    # ======================================================================================================

    def Rubrique_locations(self, rubrique):
        d1, d2 = self.Periode()

        def locations(n1=False):
            debut, fin = self.Periode(n1)
            return Location.objects.filter(date_debut__date__lte=fin).filter(Q(date_fin__isnull=True) | Q(date_fin__date__gte=debut))

        valeurs = list(locations().values_list("idlocation", "produit__nom", "produit__categorie__nom", "date_debut", "date_fin", "famille_id", "quantite"))
        if not valeurs:
            return
        nbre_n1 = locations(n1=True).count() if self.comparer else None
        durees = [(v[4] - v[3]).total_seconds() / 3600 for v in valeurs if v[3] and v[4] and v[4] > v[3]]
        montant = self.Somme(Prestation.objects.filter(location_id__in=[v[0] for v in valeurs]))

        rubrique.Add(Bloc_kpis([
            Kpi("Locations", len(valeurs), nbre_n1),
            Kpi("Familles", len(set(v[5] for v in valeurs)), None),
            Kpi("Durée moyenne", sum(durees) / len(durees) / 24 if durees else None, None, "decimal", detail="jours") if durees else None,
            Kpi("Montant facturé", montant, None, "montant") if montant else None,
        ]))

        produits = Counter(v[1] for v in valeurs)
        heures_produits = defaultdict(float)
        for v in valeurs:
            if v[3] and v[4] and v[4] > v[3]:
                heures_produits[v[1]] += (v[4] - v[3]).total_seconds() / 3600
        lignes = [[p, n, Format_nombre(heures_produits[p] / 24, "decimal"), Format_nombre(Pct(n, len(valeurs)), "pourcent")] for p, n in produits.most_common()]
        rubrique.Add(Bloc_tableau("Locations par produit", ["Produit", "Locations", "Jours loués", "Part"], lignes, ["texte", "entier", "texte", "texte"]))
        categories = Counter(v[2] or "Sans catégorie" for v in valeurs)
        if len(categories) > 1:
            labels, valeurs_c = self.Top(categories, limite=6)
            rubrique.Add(Bloc_camembert("Locations par catégorie de produit", labels, valeurs_c))
        par_date = Counter(v[3].date() for v in valeurs if v[3])
        rubrique.Add(Bloc_barres("Locations par mois (date de début)", self.labels_mois, [Serie("Locations", self.Par_mois(par_date))]))

        phrases = []
        evol = self.Phrase_evol(len(valeurs), nbre_n1, masculin=False)
        phrases.append("%s locations ont été enregistrées pour %s familles%s." % (Format_nombre(len(valeurs)), Format_nombre(len(set(v[5] for v in valeurs))), (" (%s)" % evol) if evol else ""))
        if produits:
            top = produits.most_common(1)[0]
            phrases.append("Le produit le plus loué est « %s » (%s locations)." % (top[0], Format_nombre(top[1])))
        if self.analyses:
            rubrique.Add(Bloc_analyse(phrases))

    # ======================================================================================================
    # TRANSPORTS
    # ======================================================================================================

    def Rubrique_transports(self, rubrique):
        d1, d2 = self.Periode()
        transports = Transport.objects.filter(Q(depart_date__range=(d1, d2)) | Q(date_debut__lte=d2, date_fin__gte=d1))
        valeurs = list(transports.values_list("categorie", "ligne__nom", "individu_id", "date_debut"))
        if not valeurs:
            return
        labels_categories = dict(Transport._meta.get_field("categorie").choices)
        individus = set(v[2] for v in valeurs)
        programmations = sum(1 for v in valeurs if v[3])

        rubrique.Add(Bloc_kpis([
            Kpi("Transports enregistrés", len(valeurs), None),
            Kpi("Individus transportés", len(individus), None),
            Kpi("Programmations", programmations, None, detail="%d transports ponctuels" % (len(valeurs) - programmations)),
        ]))
        categories = Counter(labels_categories.get(v[0], v[0]) for v in valeurs)
        labels, valeurs_c = self.Top(categories, limite=7)
        rubrique.Add(Bloc_camembert("Transports par catégorie", labels, valeurs_c))
        lignes_t = Counter(v[1] for v in valeurs if v[1])
        if lignes_t:
            rubrique.Add(Bloc_tableau("Transports par ligne", ["Ligne", "Transports", "Part"], self.Lignes_simples(lignes_t, sum(lignes_t.values()), limite=NBRE_MAX_LIGNES), ["texte", "entier", "texte"]))

        phrases = ["%s transports concernent %s individus sur la période." % (Format_nombre(len(valeurs)), Format_nombre(len(individus)))]
        if categories:
            top = categories.most_common(1)[0]
            phrases.append("La catégorie la plus utilisée est « %s » (%s)." % (top[0], Format_nombre(Pct(top[1], len(valeurs)), "pourcent")))
        if self.analyses:
            rubrique.Add(Bloc_analyse(phrases))

    # ======================================================================================================
    # PORTAIL
    # ======================================================================================================

    def Rubrique_portail(self, rubrique):
        d1, d2 = self.Periode()

        def connexions(n1=False):
            debut, fin = self.Periode(n1)
            return Historique.objects.filter(portail=True, titre="Connexion au portail", horodatage__date__range=(debut, fin))

        def reservations(n1=False, titre="Ajout d'une consommation"):
            debut, fin = self.Periode(n1)
            return Historique.objects.filter(portail=True, titre=titre, activite_id__in=self.ids_activites, horodatage__date__range=(debut, fin))

        familles_scope = self.Familles_presentes() or self.Familles_scope()
        comptes_actifs = Famille.objects.filter(pk__in=familles_scope, internet_actif=True).count()
        cx = connexions()
        nbre_connexions = cx.count()
        familles_connectees = set(cx.values_list("famille_id", flat=True).distinct()) - {None}
        familles_connectees_scope = familles_connectees & set(familles_scope)
        nbre_reservations = reservations().count()
        nbre_suppressions = reservations(titre="Suppression d'une consommation").count()
        renseignements = PortailRenseignement.objects.filter(date__date__range=(d1, d2))
        messages = PortailMessage.objects.filter(date_creation__date__range=(d1, d2), utilisateur__isnull=True)

        if not nbre_connexions and not nbre_reservations and not renseignements.exists():
            return

        rubrique.Add(Bloc_kpis([
            Kpi("Connexions", nbre_connexions, connexions(n1=True).count() if self.comparer else None),
            Kpi("Familles connectées", len(familles_connectees), len(set(connexions(n1=True).values_list("famille_id", flat=True).distinct()) - {None}) if self.comparer else None),
            Kpi("Taux d'utilisation", Pct(len(familles_connectees_scope), len(familles_scope)), None, "pourcent", detail="des familles concernées") if familles_scope else None,
            Kpi("Réservations en ligne", nbre_reservations, reservations(n1=True).count() if self.comparer else None),
            Kpi("Annulations en ligne", nbre_suppressions, None),
            Kpi("Renseignements modifiés", renseignements.count(), None),
        ]))

        # Connexions par mois
        par_date = Counter(d.date() for d in cx.values_list("horodatage", flat=True))
        par_date_n1 = Counter(d.date() for d in connexions(n1=True).values_list("horodatage", flat=True)) if self.comparer else {}
        rubrique.Add(Bloc_barres("Connexions au portail par mois", self.labels_mois, self.Series_mensuelles(par_date, par_date_n1, "Connexions")))

        # Réservations par activité
        if nbre_reservations:
            dict_n = dict(reservations().values_list("activite__nom").annotate(nbre=Count("idaction")))
            dict_n1 = dict(reservations(n1=True).values_list("activite__nom").annotate(nbre=Count("idaction"))) if self.comparer else {}
            lignes = self.Lignes_comparatives(dict_n, dict_n1)
            colonnes, formats = self.Colonnes_comparatives("Activité", "Réservations")
            rubrique.Add(Bloc_tableau("Réservations en ligne par activité", colonnes, lignes, formats))
            # Part des consommations réservées en ligne
            total_conso = self.Conso().count()
            if total_conso:
                rubrique.Add(Bloc_note("Les réservations effectuées depuis le portail correspondent à %s du nombre total de consommations de la période." % Format_nombre(min(Pct(nbre_reservations, total_conso), 100), "pourcent")))

        # Connexions par jour et par heure
        heures = Counter(d.hour for d in cx.values_list("horodatage", flat=True))
        if heures:
            index = list(range(min(heures), max(heures) + 1))
            rubrique.Add(Bloc_barres("Connexions par heure de la journée", ["%dh" % h for h in index], [Serie("Connexions", [heures.get(h, 0) for h in index])]))

        # Renseignements
        if renseignements.exists():
            labels_cat = {}
            try:
                from core.models import LISTE_TYPES_RENSEIGNEMENTS
                labels_cat = dict(LISTE_TYPES_RENSEIGNEMENTS)
            except ImportError:
                pass
            categories = Counter(labels_cat.get(c, c) for c in renseignements.values_list("categorie", flat=True))
            etats = Counter(renseignements.values_list("etat", flat=True))
            lignes = self.Lignes_simples(categories, sum(categories.values()), limite=NBRE_MAX_LIGNES)
            rubrique.Add(Bloc_tableau("Renseignements modifiés par catégorie", ["Catégorie", "Modifications", "Part"], lignes, ["texte", "entier", "texte"]))
            rubrique.Add(Bloc_note("Traitement des demandes : %s." % ", ".join("%s %s" % (Format_nombre(n), {"ATTENTE": "en attente", "VALIDE": "validées", "REFUS": "refusées"}.get(str(e).upper(), str(e).lower())) for e, n in etats.most_common())))

        # Paiements en ligne
        paiements = Paiement.objects.filter(horodatage__date__range=(d1, d2), reglements__isnull=False).distinct()
        if paiements.exists():
            rubrique.Add(Bloc_note("%s paiements en ligne ont abouti sur la période." % Format_nombre(paiements.count())))

        # Analyse
        phrases = []
        if familles_scope:
            phrases.append("%s des familles concernées disposent d'un compte portail actif et %s se sont connectées au moins une fois sur la période." % (Format_nombre(Pct(comptes_actifs, len(familles_scope)), "pourcent"), Format_nombre(Pct(len(familles_connectees_scope), len(familles_scope)), "pourcent")))
            if Pct(len(familles_connectees_scope), len(familles_scope)) >= 50:
                self.Fait("%s des familles utilisent le portail famille." % Format_nombre(Pct(len(familles_connectees_scope), len(familles_scope)), "pourcent"), 5)
        evol = self.Phrase_evol(nbre_connexions, connexions(n1=True).count() if self.comparer else None, masculin=False)
        phrases.append("%s connexions ont été enregistrées%s, soit %s connexions par famille connectée." % (Format_nombre(nbre_connexions), (", %s" % evol) if evol else "", Format_nombre(nbre_connexions / len(familles_connectees), "decimal") if familles_connectees else "0"))
        if nbre_reservations:
            phrases.append("Les familles ont effectué %s réservations et %s annulations directement en ligne." % (Format_nombre(nbre_reservations), Format_nombre(nbre_suppressions)))
        if heures:
            heure_max = max(heures, key=heures.get)
            phrases.append("Les connexions sont les plus nombreuses entre %dh et %dh." % (heure_max, heure_max + 1))
        if messages.exists():
            phrases.append("%s messages ont été adressés par les familles via la messagerie du portail." % Format_nombre(messages.count()))
        if self.analyses:
            rubrique.Add(Bloc_analyse(phrases))

    # ======================================================================================================
    # COMMUNICATION
    # ======================================================================================================

    def Rubrique_communication(self, rubrique):
        d1, d2 = self.Periode()
        emails = Destinataire.objects.filter(date_envoi__date__range=(d1, d2))
        sms = DestinataireSMS.objects.filter(date_envoi__date__range=(d1, d2))
        nbre_emails, nbre_sms = emails.filter(resultat_envoi="ok").count(), sms.filter(resultat_envoi="ok").count()
        if not emails.exists() and not sms.exists():
            return
        echecs_emails = emails.exclude(resultat_envoi="ok").count()
        def emails_n1():
            return Destinataire.objects.filter(date_envoi__date__range=self.Periode(n1=True), resultat_envoi="ok").count()
        def sms_n1():
            return DestinataireSMS.objects.filter(date_envoi__date__range=self.Periode(n1=True), resultat_envoi="ok").count()
        campagnes = Mail.objects.filter(destinataires__in=emails).distinct().count()

        rubrique.Add(Bloc_kpis([
            Kpi("Emails envoyés", nbre_emails, emails_n1() if self.comparer else None),
            Kpi("Envois d'emails", campagnes, None, detail="emails distincts"),
            Kpi("Taux d'échec emails", Pct(echecs_emails, emails.count()), None, "pourcent", inverse=True),
            Kpi("SMS envoyés", nbre_sms, sms_n1() if self.comparer else None) if sms.exists() else None,
        ]))

        # Par mois
        par_date_emails = Counter(d.date() for d in emails.filter(resultat_envoi="ok").values_list("date_envoi", flat=True))
        series = [Serie("Emails", self.Par_mois(par_date_emails))]
        if sms.exists():
            series.insert(0, Serie("SMS", self.Par_mois(Counter(d.date() for d in sms.filter(resultat_envoi="ok").values_list("date_envoi", flat=True))), "comparaison"))
        rubrique.Add(Bloc_barres("Emails et SMS envoyés par mois", self.labels_mois, series))

        # Par catégorie d'email
        categories = Counter(Mail.objects.filter(destinataires__in=emails.filter(resultat_envoi="ok")).values_list("categorie", flat=True))
        if categories:
            labels = {"saisie_libre": "Saisie libre", "facture": "Factures", "rappel": "Rappels", "recu_reglement": "Reçus de règlement", "portail": "Portail",
                      "attestation_presence": "Attestations de présence", "devis": "Devis", "cotisation": "Adhésions", "location": "Locations"}
            compteur = Counter()
            for categorie, nbre in categories.items():
                compteur[labels.get(categorie, (categorie or "Autre").replace("_", " ").capitalize())] += nbre
            rubrique.Add(Bloc_tableau("Emails envoyés par catégorie", ["Catégorie", "Emails", "Part"], self.Lignes_simples(compteur, sum(compteur.values())), ["texte", "entier", "texte"]))

        phrases = []
        evol = self.Phrase_evol(nbre_emails, emails_n1() if self.comparer else None)
        phrases.append("%s emails ont été envoyés avec succès%s." % (Format_nombre(nbre_emails), (" (%s)" % evol) if evol else ""))
        if echecs_emails:
            phrases.append("%s envois ont échoué (%s) : la vérification des adresses email des familles est recommandée." % (Format_nombre(echecs_emails), Format_nombre(Pct(echecs_emails, emails.count()), "pourcent")))
        if nbre_sms:
            phrases.append("%s SMS ont également été envoyés." % Format_nombre(nbre_sms))
        if self.analyses:
            rubrique.Add(Bloc_analyse(phrases))

    # ======================================================================================================
    # PERSONNEL
    # ======================================================================================================

    def Rubrique_personnel(self, rubrique):
        d1, d2 = self.Periode()
        contrats = ContratCollaborateur.objects.filter(date_debut__lte=d2).filter(Q(date_fin__isnull=True) | Q(date_fin__gte=d1))
        valeurs = list(contrats.values_list("collaborateur_id", "type_poste__nom", "date_debut", "date_fin"))
        if not valeurs:
            return
        collaborateurs = set(v[0] for v in valeurs)
        nouveaux = sum(1 for v in valeurs if d1 <= v[2] <= d2)
        termines = sum(1 for v in valeurs if v[3] and d1 <= v[3] <= d2)
        p1, p2 = self.Periode(n1=True)
        nbre_n1 = ContratCollaborateur.objects.filter(date_debut__lte=p2).filter(Q(date_fin__isnull=True) | Q(date_fin__gte=p1)).values("collaborateur_id").distinct().count() if self.comparer else None

        rubrique.Add(Bloc_kpis([
            Kpi("Collaborateurs", len(collaborateurs), nbre_n1),
            Kpi("Contrats actifs", len(valeurs), None),
            Kpi("Contrats débutés", nouveaux, None),
            Kpi("Contrats terminés", termines, None),
        ]))
        postes = Counter(v[1] or "Non renseigné" for v in valeurs)
        rubrique.Add(Bloc_tableau("Contrats par type de poste", ["Poste", "Contrats", "Part"], self.Lignes_simples(postes, len(valeurs)), ["texte", "entier", "texte"]))
        if len(postes) > 1:
            labels, valeurs_p = self.Top(postes, limite=7)
            rubrique.Add(Bloc_camembert("Répartition par type de poste", labels, valeurs_p))
        qualifications = Counter(Collaborateur.objects.filter(pk__in=collaborateurs).values_list("qualifications__nom", flat=True))
        qualifications.pop(None, None)
        if qualifications:
            rubrique.Add(Bloc_tableau("Qualifications des collaborateurs", ["Qualification", "Collaborateurs", "Part"], self.Lignes_simples(qualifications, len(collaborateurs)), ["texte", "entier", "texte"]))
        phrases = ["%s collaborateurs disposaient d'un contrat actif sur la période (%s contrats). %s contrats ont débuté et %s se sont terminés." % (Format_nombre(len(collaborateurs)), Format_nombre(len(valeurs)), Format_nombre(nouveaux), Format_nombre(termines))]
        if self.analyses:
            rubrique.Add(Bloc_analyse(phrases))

    # ======================================================================================================
    # APPLICATION
    # ======================================================================================================

    def Rubrique_application(self, rubrique):
        d1, d2 = self.Periode()
        actions = Historique.objects.filter(horodatage__date__range=(d1, d2), portail=False)
        nbre = actions.count()
        if not nbre:
            return
        nbre_n1 = Historique.objects.filter(horodatage__date__range=self.Periode(n1=True), portail=False).count() if self.comparer else None
        utilisateurs = actions.values("utilisateur_id").distinct().count()

        rubrique.Add(Bloc_kpis([
            Kpi("Actions enregistrées", nbre, nbre_n1),
            Kpi("Utilisateurs actifs", utilisateurs, None),
            Kpi("Actions par jour ouvré", nbre / max(1, sum(1 for i in range((d2 - d1).days + 1) if (d1 + datetime.timedelta(days=i)).weekday() < 5)), None, "decimal"),
        ]))
        titres = dict(actions.values_list("titre").annotate(nbre=Count("idaction")).order_by("-nbre")[:NBRE_MAX_LIGNES])
        rubrique.Add(Bloc_tableau("Actions les plus fréquentes", ["Action", "Nombre", "Part"], [[k, v, Format_nombre(Pct(v, nbre), "pourcent")] for k, v in sorted(titres.items(), key=lambda x: -x[1])], ["texte", "entier", "texte"]))
        par_date = dict(actions.values_list("horodatage__date").annotate(nbre=Count("idaction")))
        par_date_n1 = dict(Historique.objects.filter(horodatage__date__range=self.Periode(n1=True), portail=False).values_list("horodatage__date").annotate(nbre=Count("idaction"))) if self.comparer else {}
        rubrique.Add(Bloc_barres("Actions par mois", self.labels_mois, self.Series_mensuelles(par_date, par_date_n1, "Actions")))
        jours = Counter()
        for date, n in par_date.items():
            jours[date.weekday()] += n
        index = [i for i in range(7) if jours.get(i)]
        rubrique.Add(Bloc_barres("Actions par jour de la semaine", [JOURS[i] for i in index], [Serie("Actions", [jours[i] for i in index])]))
        utilisateurs_actions = {(prenom or nom or username or "Inconnu") if not (prenom and nom) else "%s %s" % (prenom, nom): n for prenom, nom, username, n in
                                actions.values_list("utilisateur__first_name", "utilisateur__last_name", "utilisateur__username").annotate(nbre=Count("idaction")).order_by("-nbre")[:NBRE_MAX_LIGNES]}
        if utilisateurs_actions:
            rubrique.Add(Bloc_tableau("Actions par utilisateur", ["Utilisateur", "Actions", "Part"], [[k, v, Format_nombre(Pct(v, nbre), "pourcent")] for k, v in utilisateurs_actions.items()], ["texte", "entier", "texte"]))
        phrases = []
        evol = self.Phrase_evol(nbre, nbre_n1, masculin=False)
        phrases.append("%s actions ont été enregistrées dans l'historique par %s %s%s." % (Format_nombre(nbre), Format_nombre(utilisateurs), Pluriel(utilisateurs, "utilisateur"), (", un volume %s" % evol) if evol else ""))
        if titres:
            top = max(titres.items(), key=lambda x: x[1])
            phrases.append("L'action la plus fréquente est « %s » (%s)." % (top[0], Format_nombre(Pct(top[1], nbre), "pourcent")))
        if self.analyses:
            rubrique.Add(Bloc_analyse(phrases))

    # ======================================================================================================
    # ANNEXES
    # ======================================================================================================

    def Rubrique_annexes(self, rubrique):
        # Consommations par activité et par mois
        donnees = defaultdict(Counter)
        for activite, date, nbre in self.Conso().values_list("activite__nom", "date").annotate(nbre=Count("idconso")):
            donnees[activite][(date.year, date.month)] += nbre
        if donnees:
            self.Annexe_mensuelle(rubrique, "Consommations par activité et par mois", donnees, "entier")
        # Individus distincts par activité et par mois
        donnees = defaultdict(Counter)
        for activite, annee, mois, nbre in self.Conso().values_list("activite__nom", "date__year", "date__month").annotate(nbre=Count("individu_id", distinct=True)):
            donnees[activite][(annee, mois)] += nbre
        if donnees:
            self.Annexe_mensuelle(rubrique, "Individus distincts par activité et par mois", donnees, "entier", total=False)
        # Prestations par activité et par mois
        donnees = defaultdict(Counter)
        for activite, date, montant in self.Prestations().values_list("activite__nom", "date").annotate(total=Sum("montant")):
            donnees[activite or "Hors activité"][(date.year, date.month)] += float(montant or 0)
        if donnees:
            self.Annexe_mensuelle(rubrique, "Montant des prestations par activité et par mois", donnees, "montant")
        # Paramètres
        lignes = [["Période", "Du %s au %s" % (self.d1.strftime("%d/%m/%Y"), self.d2.strftime("%d/%m/%Y"))]]
        if self.comparer:
            lignes.append(["Période de comparaison", "Du %s au %s" % (self.p1.strftime("%d/%m/%Y"), self.p2.strftime("%d/%m/%Y"))])
        lignes.append(["États des consommations retenus", ", ".join(ETATS_LABELS.get(e, e) for e in self.etats)])
        lignes.append(["Activités", ", ".join(sorted(self.dict_activites.values()))])
        rubrique.Add(Bloc_tableau("Paramètres de calcul", ["Paramètre", "Valeur"], lignes, ["texte", "texte"]))

    def Annexe_mensuelle(self, rubrique, titre, donnees, format="entier", total=True):
        """ Tableau activité x mois, découpé par blocs de 6 mois pour tenir sur la largeur """
        for index in range(0, len(self.mois), 6):
            mois = self.mois[index:index + 6]
            labels = self.labels_mois[index:index + 6]
            lignes = []
            for activite in sorted(donnees):
                valeurs = [donnees[activite].get(m, 0) for m in mois]
                if any(valeurs):
                    lignes.append([activite] + valeurs + ([sum(valeurs)] if total else []))
            if not lignes:
                continue
            colonnes = ["Activité"] + labels + (["Total"] if total else [])
            ligne_total = ["Total"] + [sum(float(l[i] or 0) for l in lignes) for i in range(1, len(colonnes))] if total else None
            suffixe = " (%s à %s)" % (labels[0], labels[-1]) if len(self.mois) > 6 else ""
            rubrique.Add(Bloc_tableau(titre + suffixe, colonnes, lignes, ["texte"] + [format] * (len(colonnes) - 1), total=ligne_total))
