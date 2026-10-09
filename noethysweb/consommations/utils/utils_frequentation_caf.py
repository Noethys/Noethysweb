# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

"""
Moteur de calcul de la fonction "Fréquentation CAF".

Il reprend fidèlement les règles de calcul de l'état global (consommations/utils/utils_impression_etat_global.py)
et y ajoute :
    - deux comptages simultanés (réalisé / facturé), chacun avec ses états et ses méthodes de calcul par unité,
    - des filtres de population (questionnaires, régime, caisse, âge, QF) en mode "uniquement" ou "dont",
    - un évaluateur de formules sécurisé (aucun eval()),
    - des contrôles qualité,
    - une ventilation supplémentaire des périodes : mercredis / autres jours hors vacances / vacances.
"""

import ast, datetime, json, logging, re
logger = logging.getLogger(__name__)
from django.db.models import Q
from django.urls import reverse
from core.models import Activite, Unite, Consommation, Vacance, Regime, Caisse, Famille, Individu, Quotient, TarifLigne, Evenement, \
                        QuestionnaireQuestion, QuestionnaireReponse, QuestionnaireChoix, Rattachement
from core.utils import utils_dates


# ------------------------------------------------------------------------------------------------------------------
# Constantes
# ------------------------------------------------------------------------------------------------------------------

COLONNES = (("realise", "Réalisé"), ("facture", "Facturé"))
LABELS_HEURES = {"realise": "Heures réalisées", "facture": "Heures facturées"}

ETATS = (("present", "Présent"), ("absenti", "Absence injustifiée"), ("absentj", "Absence justifiée"), ("reservation", "Réservation (non pointée)"))
ETATS_DEFAUT = {"realise": ["present"], "facture": ["present", "absenti", "reservation"]}

TYPES_CALCUL = (
    ("1", "Temps réel de présence"),
    ("2", "Temps facturé (tarif)"),
    ("4", "Équivalence en heures"),
    ("0", "Nombre d'unités × durée"),
    ("3", "Formule"),
)

ARRONDIS = (
    ("", "Aucun arrondi"),
    ("duree;5", "Durée : 5 minutes entamées"),
    ("duree;10", "Durée : 10 minutes entamées"),
    ("duree;15", "Durée : quart d'heure entamé"),
    ("duree;30", "Durée : demi-heure entamée"),
    ("duree;60", "Durée : heure entamée"),
    ("tranche_horaire;5", "Horaires : tranches de 5 minutes"),
    ("tranche_horaire;10", "Horaires : tranches de 10 minutes"),
    ("tranche_horaire;15", "Horaires : tranches d'un quart d'heure"),
    ("tranche_horaire;30", "Horaires : tranches d'une demi-heure"),
    ("tranche_horaire;60", "Horaires : tranches d'une heure"),
)

VENTILATIONS_PERIODES = (
    ("mercredis", "Mercredis, autres jours scolaires, petites vacances, été"),
    ("simple", "Hors vacances, petites vacances, été"),
    ("detaillees", "Périodes détaillées (chaque période de vacances et d'école)"),
)

# Repris de l'état global, dans le même ordre
REGROUPEMENTS = [("aucun", "Aucun"), ("jour", "Jour"), ("mois", "Mois"), ("annee", "Année"),
    ("activite", "Activité"), ("groupe", "Groupe"), ("evenement", "Evènement"),
    ("evenement_date", "Evènement (avec date)"),
    ("unite_conso", "Unité de consommation"), ("categorie_tarif", "Catégorie de tarif"),
    ("ville_residence", "Ville de résidence"), ("secteur", "Secteur géographique"),
    ("genre", "Genre (M/F)"), ("age", "Age"), ("ville_naissance", "Ville de naissance"),
    ("nom_ecole", "Ecole"), ("nom_classe", "Classe"), ("nom_niveau_scolaire", "Niveau scolaire"),
    ("individu", "Individu"), ("famille", "Famille"), ("regime", "Régime social"),
    ("caisse", "Caisse d'allocations"), ("qf_perso", "Quotient familial (tranches personnalisées)"),
    ("qf_tarifs", "Quotient familial (tranches paramétrées)"),
    ("qf_100", "Quotient familial (tranches de 100)"), ("categorie_travail", "Catégorie de travail"),
    ("categorie_travail_pere", "Catégorie de travail du père"),
    ("categorie_travail_mere", "Catégorie de travail de la mère")]

# Regroupements qui nécessitent le chargement des informations individuelles complètes
REGROUPEMENTS_INFOS = ("ville_residence", "secteur", "genre", "ville_naissance", "nom_ecole", "nom_classe", "nom_niveau_scolaire",
                       "individu", "famille", "categorie_travail", "categorie_travail_pere", "categorie_travail_mere")

# Filtres de population : opérateurs selon le type de donnée
OPERATEURS = {
    "coche": (("coche", "est cochée"), ("non_coche", "n'est pas cochée")),
    "choix": (("parmi", "est l'une de"), ("hors", "n'est aucune de")),
    "texte": (("contient", "contient"), ("egal", "est égale à"), ("vide", "n'est pas renseignée"), ("non_vide", "est renseignée")),
    "nombre": (("egal", "est égal à"), ("sup", "est supérieur ou égal à"), ("inf", "est inférieur ou égal à"), ("entre", "est compris entre"), ("vide", "n'est pas renseigné")),
    "date": (("avant", "est avant le"), ("apres", "est après le"), ("entre", "est comprise entre"), ("vide", "n'est pas renseignée")),
    "liste": (("parmi", "est l'un de"), ("hors", "n'est aucun de")),
}
FILTRES_QUESTIONS_CONTROLES = {"case_coche": "coche", "liste_deroulante": "choix", "liste_deroulante_avancee": "choix", "liste_coches": "choix",
                               "ligne_texte": "texte", "bloc_texte": "texte", "codebarres": "texte", "entier": "nombre", "slider": "nombre",
                               "decimal": "nombre", "montant": "nombre", "date": "date"}

ZERO = datetime.timedelta(0)
REGEX_HHMM = re.compile(r"^\s*(\d{1,3})\s*[:hH]\s*(\d{0,2})\s*$")
JOURS_TOUS = ["0", "1", "2", "3", "4", "5", "6"]


# ------------------------------------------------------------------------------------------------------------------
# Utilitaires
# ------------------------------------------------------------------------------------------------------------------

class Erreur_parametres(Exception):
    pass


def Formater_duree(valeur, mode="decimal"):
    """ Formate une durée (timedelta) comme l'état global : décimal (8.5) ou horaire (8h30) """
    if valeur is None:
        valeur = ZERO
    if mode == "horaire":
        secondes = int(valeur.total_seconds())
        signe = "-" if secondes < 0 else ""
        secondes = abs(secondes)
        return "%s%dh%02d" % (signe, secondes // 3600, (secondes % 3600) // 60)
    texte = "{:,.2f}".format(round(valeur.total_seconds() / 3600, 2))
    return texte.replace(",", " ").replace(".", ",")


def Heures(valeur):
    return round((valeur or ZERO).total_seconds() / 3600, 2)


def Valider_hhmm(texte, libelle=""):
    """ Vérifie qu'une durée ou une heure est au format hh:mm. Retourne la valeur normalisée ou "" """
    if not texte:
        return ""
    resultat = REGEX_HHMM.match(str(texte))
    if not resultat or int(resultat.group(2) or 0) > 59:
        raise Erreur_parametres("%s : la valeur '%s' doit être au format hh:mm." % (libelle, texte))
    return "%02d:%02d" % (int(resultat.group(1)), int(resultat.group(2) or 0))


def Age(date_naiss=None, date=None):
    if not date_naiss:
        return -1
    return (date.year - date_naiss.year) - int((date.month, date.day) < (date_naiss.month, date_naiss.day))


def Get_activites_autorisees(selection=None, request=None):
    """ Retourne les activités sélectionnées, limitées aux structures de l'utilisateur """
    if isinstance(selection, str):
        selection = json.loads(selection)
    if selection["type"] == "groupes_activites":
        activites = Activite.objects.filter(groupes_activites__in=selection["ids"])
    elif selection["type"] == "groupes":
        activites = Activite.objects.filter(groupe__in=selection["ids"])
    elif selection["type"] == "toutes":
        activites = Activite.objects.all()
    else:
        activites = Activite.objects.filter(pk__in=selection["ids"])
    if request:
        activites = activites.filter(structure__in=request.user.structures.all())
    return activites.distinct().order_by("date_debut", "nom")


def Filtrer_activites_periode(activites=None, date_debut=None, date_fin=None):
    """ Conserve uniquement les activités ouvertes sur la période """
    condition_periode = (Q(date_debut__lte=date_fin) | Q(date_debut__isnull=True)) & (Q(date_fin__gte=date_debut) | Q(date_fin__isnull=True))
    return activites.filter(condition_periode)


def Get_unites(activites=None, date_debut=None, date_fin=None):
    """ Unités des activités ouvertes sur la période, regroupées par activité, avec les méthodes suggérées """
    activites = Filtrer_activites_periode(activites, date_debut, date_fin)
    unites = Unite.objects.select_related("activite").filter(activite__in=activites).order_by("activite__date_debut", "activite_id", "ordre")

    # Unités pour lesquelles des prestations de la période ont un temps facturé
    unites_temps_facture = set(Consommation.objects.filter(unite__in=unites, date__gte=date_debut, date__lte=date_fin,
                                                           prestation__temps_facture__isnull=False).values_list("unite_id", flat=True).distinct())

    liste_activites = []
    dict_activites = {}
    for unite in unites:
        if unite.activite_id not in dict_activites:
            dict_activites[unite.activite_id] = {"id": unite.activite_id, "nom": unite.activite.nom, "unites": []}
            liste_activites.append(dict_activites[unite.activite_id])
        dict_activites[unite.activite_id]["unites"].append(Suggerer_methodes(unite, avec_temps_facture=unite.pk in unites_temps_facture))
    return liste_activites


def Suggerer_methodes(unite=None, avec_temps_facture=False):
    """ Propose une méthode de calcul pour chaque colonne en fonction du paramétrage de l'unité """
    a_horaires = unite.type in ("Horaire", "Multihoraires") or bool(unite.heure_debut and unite.heure_fin)
    equiv_heures = utils_dates.TimeEnDelta(unite.equiv_heures) if unite.equiv_heures else None
    coeff = None
    if unite.coeff:
        try:
            coeff = float(str(unite.coeff).replace(",", "."))
        except ValueError:
            coeff = None

    def Parametres(type_calcul="1", coeff_temp=""):
        return {"type": type_calcul, "coeff": coeff_temp, "formule": "", "arrondi": "", "duree_seuil": "", "duree_plafond": "", "heure_seuil": "", "heure_plafond": ""}

    remarque = ""
    actif = True
    if a_horaires:
        realise = Parametres("1")
        remarque = "Unité avec horaires"
    elif equiv_heures:
        realise = Parametres("4")
        remarque = "Équivalence paramétrée"
    elif coeff:
        realise = Parametres("0", Formater_coeff(coeff))
        remarque = "Coefficient paramétré"
    else:
        realise = Parametres("0", "")
        actif = False
        remarque = "Unité sans horaire ni équivalence"

    if avec_temps_facture:
        facture = Parametres("2")
    elif equiv_heures:
        facture = Parametres("4")
    else:
        facture = dict(realise)

    return {
        "id": unite.pk, "nom": unite.nom, "type_unite": unite.type, "actif": actif, "remarque": remarque,
        "equiv_heures": Formater_duree(equiv_heures, "horaire") if equiv_heures else "",
        "horaires": "%s - %s" % (unite.heure_debut.strftime("%Hh%M"), unite.heure_fin.strftime("%Hh%M")) if unite.heure_debut and unite.heure_fin else "",
        "parametres": {"realise": realise, "facture": facture},
    }


def Formater_coeff(coeff):
    """ Coefficient en heures décimales -> hh:mm (plus parlant pour un débutant) """
    minutes = int(round(float(coeff) * 60))
    return "%02d:%02d" % (minutes // 60, minutes % 60)


def Coeff_en_delta(coeff=""):
    """ Accepte un coefficient décimal (1.5) comme dans l'état global ou une durée (01:30) """
    if coeff in (None, ""):
        return ZERO
    texte = str(coeff).strip()
    if REGEX_HHMM.match(texte):
        return utils_dates.HeureStrEnDelta(Valider_hhmm(texte, "Coefficient"))
    return datetime.timedelta(hours=float(texte.replace(",", ".")))


# ------------------------------------------------------------------------------------------------------------------
# Évaluateur de formules sécurisé (remplace eval())
# ------------------------------------------------------------------------------------------------------------------

class Unite_conso():
    """ Données d'une unité pour une date et une inscription (identique à l'état global) """
    ATTRIBUTS = ("idunite", "debut", "fin", "etat", "duree", "quantite")

    def __init__(self, IDunite=None, heure_debut=None, heure_fin=None, etat=None, quantite=1):
        self.idunite = IDunite
        self.debut = utils_dates.TimeEnDelta(heure_debut)
        self.fin = utils_dates.TimeEnDelta(heure_fin)
        self.etat = etat
        self.duree = self.fin - self.debut
        self.quantite = quantite if etat else 0


def _SI(condition=None, alors=None, sinon=ZERO):
    return alors if condition else sinon


FONCTIONS_FORMULE = {
    "SI": _SI,
    "HEURE": utils_dates.HeureStrEnDelta,
    "MIN": min,
    "MAX": max,
}

OPERATEURS_BINAIRES = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b}
OPERATEURS_COMPARAISON = {ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b, ast.Lt: lambda a, b: a < b, ast.LtE: lambda a, b: a <= b,
                          ast.Gt: lambda a, b: a > b, ast.GtE: lambda a, b: a >= b, ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b}
REGEX_UNITES = re.compile(r"\bunite([0-9]+)\b")


class Formule():
    """
    Formule de l'état global, compilée une fois et évaluée sans eval().
    Syntaxe acceptée : unite12.duree, unite12.etat == 'present', debut, fin, duree, date,
    SI(condition, alors, sinon), HEURE('08:30'), MIN(), MAX(), ET, OU, +, -, *, /, comparaisons.
    """
    def __init__(self, texte=""):
        self.texte = texte or ""
        source = self.texte.replace("\n", " ").replace("\r", " ")
        source = re.sub(r"\bET\b", " and ", source)
        source = re.sub(r"\bOU\b", " or ", source)
        source = re.sub(r"\bself\.", "", source)
        try:
            self.arbre = ast.parse(source.strip(), mode="eval")
        except SyntaxError as err:
            raise Erreur_parametres("La formule '%s' contient une erreur de syntaxe (%s)." % (self.texte, err.msg))
        self.unites = sorted({int(x) for x in REGEX_UNITES.findall(source)})
        self.Verifier(self.arbre)

    def Verifier(self, noeud):
        """ N'autorise que les éléments nécessaires aux formules """
        autorises = (ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.BinOp, ast.UnaryOp, ast.USub, ast.UAdd, ast.Not, ast.Compare,
                     ast.IfExp, ast.Call, ast.Name, ast.Load, ast.Attribute, ast.Constant, ast.Tuple, ast.List) + tuple(OPERATEURS_BINAIRES) + tuple(OPERATEURS_COMPARAISON)
        for element in ast.walk(noeud):
            if not isinstance(element, autorises):
                raise Erreur_parametres("La formule '%s' contient un élément non autorisé (%s)." % (self.texte, type(element).__name__))
            if isinstance(element, ast.Call) and (not isinstance(element.func, ast.Name) or element.func.id not in FONCTIONS_FORMULE or element.keywords):
                raise Erreur_parametres("La formule '%s' utilise une fonction non autorisée." % self.texte)
            if isinstance(element, ast.Attribute):
                if not isinstance(element.value, ast.Name) or not REGEX_UNITES.fullmatch(element.value.id) or element.attr not in Unite_conso.ATTRIBUTS:
                    raise Erreur_parametres("La formule '%s' contient une référence non valide (%s)." % (self.texte, element.attr))
            if isinstance(element, ast.Name) and element.id not in FONCTIONS_FORMULE and element.id not in ("debut", "fin", "duree", "date", "True", "False", "None") \
                    and not REGEX_UNITES.fullmatch(element.id):
                raise Erreur_parametres("La formule '%s' contient un nom inconnu : %s." % (self.texte, element.id))
            if isinstance(element, ast.Constant) and not isinstance(element.value, (int, float, str, bool, type(None))):
                raise Erreur_parametres("La formule '%s' contient une valeur non autorisée." % self.texte)

    def Calculer(self, variables={}):
        resultat = self._Evaluer(self.arbre.body, variables)
        if resultat is None or resultat is False:
            return ZERO
        if isinstance(resultat, bool):
            return ZERO
        if isinstance(resultat, (int, float)):
            return datetime.timedelta(hours=resultat)
        if not isinstance(resultat, datetime.timedelta):
            raise Erreur_parametres("La formule '%s' ne retourne pas une durée." % self.texte)
        return resultat

    def _Evaluer(self, noeud, variables):
        if isinstance(noeud, ast.Constant):
            return noeud.value
        if isinstance(noeud, ast.Name):
            if noeud.id in ("True", "False", "None"):
                return {"True": True, "False": False, "None": None}[noeud.id]
            return variables.get(noeud.id, Unite_conso() if REGEX_UNITES.fullmatch(noeud.id) else None)
        if isinstance(noeud, ast.Attribute):
            return getattr(self._Evaluer(noeud.value, variables), noeud.attr)
        if isinstance(noeud, (ast.Tuple, ast.List)):
            return tuple(self._Evaluer(element, variables) for element in noeud.elts)
        if isinstance(noeud, ast.BinOp):
            return OPERATEURS_BINAIRES[type(noeud.op)](self._Evaluer(noeud.left, variables), self._Evaluer(noeud.right, variables))
        if isinstance(noeud, ast.UnaryOp):
            valeur = self._Evaluer(noeud.operand, variables)
            if isinstance(noeud.op, ast.Not):
                return not valeur
            return -valeur if isinstance(noeud.op, ast.USub) else +valeur
        if isinstance(noeud, ast.BoolOp):
            if isinstance(noeud.op, ast.And):
                valeur = True
                for element in noeud.values:
                    valeur = self._Evaluer(element, variables)
                    if not valeur:
                        return valeur
                return valeur
            valeur = False
            for element in noeud.values:
                valeur = self._Evaluer(element, variables)
                if valeur:
                    return valeur
            return valeur
        if isinstance(noeud, ast.Compare):
            gauche = self._Evaluer(noeud.left, variables)
            for operateur, comparateur in zip(noeud.ops, noeud.comparators):
                droite = self._Evaluer(comparateur, variables)
                if not OPERATEURS_COMPARAISON[type(operateur)](gauche, droite):
                    return False
                gauche = droite
            return True
        if isinstance(noeud, ast.IfExp):
            return self._Evaluer(noeud.body, variables) if self._Evaluer(noeud.test, variables) else self._Evaluer(noeud.orelse, variables)
        if isinstance(noeud, ast.Call):
            arguments = [self._Evaluer(argument, variables) for argument in noeud.args]
            return FONCTIONS_FORMULE[noeud.func.id](*arguments)
        raise Erreur_parametres("Élément de formule non géré.")


# ------------------------------------------------------------------------------------------------------------------
# Normalisation des paramètres envoyés par la page
# ------------------------------------------------------------------------------------------------------------------

def Normaliser_parametres(donnees=None, request=None):
    """ Valide et normalise les paramètres. Lève Erreur_parametres en cas de problème. """
    if isinstance(donnees, str):
        try:
            donnees = json.loads(donnees)
        except ValueError:
            raise Erreur_parametres("Les paramètres transmis ne sont pas valides.")
    p = {}

    # Période
    try:
        p["date_debut"] = datetime.date.fromisoformat(donnees["date_debut"])
        p["date_fin"] = datetime.date.fromisoformat(donnees["date_fin"])
    except (KeyError, TypeError, ValueError):
        raise Erreur_parametres("Veuillez sélectionner une période.")
    if p["date_debut"] > p["date_fin"]:
        raise Erreur_parametres("La date de début de la période doit être antérieure à la date de fin.")

    # Activités
    try:
        selection = donnees["activites"]
        if isinstance(selection, str):
            selection = json.loads(selection)
        if selection.get("type") not in ("activites", "groupes_activites", "groupes", "toutes"):
            raise ValueError
        selection["ids"] = [int(x) for x in selection.get("ids", [])]
    except (KeyError, TypeError, ValueError):
        raise Erreur_parametres("Veuillez sélectionner des activités.")
    if selection["type"] != "toutes" and not selection["ids"]:
        raise Erreur_parametres("Veuillez sélectionner au moins une activité.")
    p["selection_activites"] = selection
    p["activites"] = list(Filtrer_activites_periode(Get_activites_autorisees(selection, request=request), p["date_debut"], p["date_fin"]))
    if not p["activites"]:
        raise Erreur_parametres("Aucune activité accessible et ouverte sur la période ne correspond à la sélection.")
    ids_activites = {activite.pk for activite in p["activites"]}

    # Jours
    p["jours_hors_vacances"] = [str(x) for x in donnees.get("jours_hors_vacances", JOURS_TOUS) if str(x) in JOURS_TOUS]
    p["jours_vacances"] = [str(x) for x in donnees.get("jours_vacances", JOURS_TOUS) if str(x) in JOURS_TOUS]
    if not p["jours_hors_vacances"] and not p["jours_vacances"]:
        raise Erreur_parametres("Veuillez cocher au moins un jour.")

    # Colonnes réalisé / facturé
    unites_valides = {unite.pk: unite for unite in Unite.objects.filter(activite_id__in=ids_activites)}
    codes_types = [code for code, label in TYPES_CALCUL]
    codes_arrondis = [code for code, label in ARRONDIS]
    p["colonnes"] = {}
    for code_colonne, label_colonne in COLONNES:
        donnees_colonne = donnees.get("colonnes", {}).get(code_colonne, {})
        if not donnees_colonne.get("active", False):
            continue
        etats = [etat for etat in donnees_colonne.get("etats", []) if etat in dict(ETATS)]
        if not etats:
            raise Erreur_parametres("Colonne %s : cochez au moins un état de consommation." % label_colonne)
        unites = {}
        for idunite, parametres in donnees_colonne.get("unites", {}).items():
            try:
                idunite = int(idunite)
            except ValueError:
                continue
            if idunite not in unites_valides:
                continue
            nom_unite = "%s (%s)" % (unites_valides[idunite].nom, label_colonne.lower())
            type_calcul = str(parametres.get("type", "1"))
            if type_calcul not in codes_types:
                raise Erreur_parametres("Unité %s : méthode de calcul inconnue." % nom_unite)
            arrondi = parametres.get("arrondi", "") or ""
            if arrondi not in codes_arrondis:
                raise Erreur_parametres("Unité %s : arrondi inconnu." % nom_unite)
            dict_unite = {
                "type": type_calcul,
                "coeff": parametres.get("coeff", "") or "",
                "formule": parametres.get("formule", "") or "",
                "arrondi": arrondi if type_calcul == "1" else "",
                "duree_seuil": Valider_hhmm(parametres.get("duree_seuil"), "Unité %s, durée minimum" % nom_unite) if type_calcul == "1" else "",
                "duree_plafond": Valider_hhmm(parametres.get("duree_plafond"), "Unité %s, durée maximum" % nom_unite) if type_calcul == "1" else "",
                "heure_seuil": Valider_hhmm(parametres.get("heure_seuil"), "Unité %s, heure de début" % nom_unite) if type_calcul == "1" else "",
                "heure_plafond": Valider_hhmm(parametres.get("heure_plafond"), "Unité %s, heure de fin" % nom_unite) if type_calcul == "1" else "",
            }
            if type_calcul == "0":
                try:
                    dict_unite["coeff_delta"] = Coeff_en_delta(dict_unite["coeff"])
                except (ValueError, Erreur_parametres):
                    raise Erreur_parametres("Unité %s : la durée par unité '%s' n'est pas valide (exemples : 8, 1.5 ou 01:30)." % (nom_unite, dict_unite["coeff"]))
            if type_calcul == "3":
                if not dict_unite["formule"].strip():
                    raise Erreur_parametres("Unité %s : veuillez saisir une formule." % nom_unite)
                dict_unite["formule_compilee"] = Formule(dict_unite["formule"])
            unites[idunite] = dict_unite
        if not unites:
            raise Erreur_parametres("Colonne %s : sélectionnez au moins une unité." % label_colonne)
        p["colonnes"][code_colonne] = {"label": label_colonne, "etats": etats, "unites": unites}
    if not p["colonnes"]:
        raise Erreur_parametres("Activez au moins une des deux colonnes (réalisé ou facturé).")

    # Règles complémentaires
    try:
        p["plafond_journalier"] = int(donnees.get("plafond_journalier") or 0)
    except (TypeError, ValueError):
        raise Erreur_parametres("Le plafond journalier doit être un nombre de minutes.")
    associer = donnees.get("associer_regime_inconnu") or ""
    p["associer_regime_inconnu"] = int(associer) if str(associer).isdigit() and Regime.objects.filter(pk=int(associer)).exists() else None

    # Présentation
    p["regroupement_principal"] = donnees.get("regroupement_principal") or "aucun"
    codes_regroupements = [code for code, label in REGROUPEMENTS] + list(Get_questions_regroupement().keys())
    if p["regroupement_principal"] not in codes_regroupements:
        raise Erreur_parametres("Le regroupement principal sélectionné n'existe pas.")
    p["regroupement_age"] = Lire_tranches(donnees.get("regroupement_age", ""), "Tranches d'âge")
    p["tranches_qf_perso"] = Lire_tranches(donnees.get("tranches_qf_perso", ""), "Tranches de QF")
    if p["regroupement_principal"] == "qf_perso" and not p["tranches_qf_perso"]:
        raise Erreur_parametres("Saisissez les tranches de QF personnalisées (exemple : 650, 800, 1200).")
    p["ventilation_periodes"] = donnees.get("ventilation_periodes") if donnees.get("ventilation_periodes") in dict(VENTILATIONS_PERIODES) else "mercredis"
    p["regroupement_regime"] = bool(donnees.get("regroupement_regime", False))
    p["format_donnees"] = "horaire" if donnees.get("format_donnees") == "horaire" else "decimal"

    # Filtres de population
    p["filtres"] = [Normaliser_filtre(filtre) for filtre in donnees.get("filtres", []) if filtre.get("champ")]

    p["donnees_brutes"] = donnees
    return p


def Lire_tranches(texte="", libelle=""):
    if not texte or not str(texte).strip():
        return []
    try:
        valeurs = [int(x) for x in str(texte).replace(";", ",").split(",") if x.strip()]
    except ValueError:
        raise Erreur_parametres("%s : saisissez des nombres entiers séparés par des virgules (exemple : 6, 12)." % libelle)
    if valeurs != sorted(set(valeurs)):
        raise Erreur_parametres("%s : les valeurs doivent être croissantes et sans doublon." % libelle)
    return valeurs


def Get_questions_regroupement():
    """ Questions individus et familles utilisables en regroupement, comme dans l'état global """
    from core.utils import utils_questionnaires
    dict_questions = {}
    q = utils_questionnaires.Questionnaires()
    for public in ("famille", "individu"):
        for dict_temp in q.GetQuestions(public):
            dict_questions["question_%s_%d" % (public, dict_temp["IDquestion"])] = "Question %s. : %s" % (public[:3], dict_temp["label"])
    return dict_questions


def Get_champs_filtres():
    """ Liste des champs utilisables dans les filtres de population (pour la page) """
    champs = []
    for question in QuestionnaireQuestion.objects.filter(categorie__in=("individu", "famille")).order_by("categorie", "ordre"):
        type_filtre = FILTRES_QUESTIONS_CONTROLES.get(question.controle)
        if not type_filtre:
            continue
        choix = []
        if question.controle == "liste_deroulante_avancee":
            choix = [(str(c.pk), c.label) for c in QuestionnaireChoix.objects.filter(question=question).order_by("ordre")]
        elif type_filtre == "choix" and question.choix:
            choix = [(c.strip(), c.strip()) for c in question.choix.split(";") if c.strip()]
        champs.append({"code": "question_%s_%d" % (question.categorie, question.pk), "label": "Question %s. : %s" % (question.categorie[:3], question.label),
                       "type": type_filtre, "choix": choix, "groupe": "Questionnaires %ss" % question.categorie})
    champs.append({"code": "regime", "label": "Régime social", "type": "liste", "groupe": "Famille",
                   "choix": [("0", "- Régime inconnu -")] + [(str(r.pk), r.nom) for r in Regime.objects.all().order_by("nom")]})
    champs.append({"code": "caisse", "label": "Caisse d'allocations", "type": "liste", "groupe": "Famille",
                   "choix": [("0", "- Caisse inconnue -")] + [(str(c.pk), c.nom) for c in Caisse.objects.all().order_by("nom")]})
    champs.append({"code": "qf", "label": "Quotient familial (à la date de la consommation)", "type": "nombre", "choix": [], "groupe": "Famille"})
    champs.append({"code": "age", "label": "Âge (à la date de la consommation)", "type": "nombre", "choix": [], "groupe": "Individu"})
    return champs


def Normaliser_filtre(filtre={}):
    champ = filtre.get("champ")
    champs = {c["code"]: c for c in Get_champs_filtres()}
    if champ not in champs:
        raise Erreur_parametres("Un filtre porte sur un champ qui n'existe plus.")
    definition = champs[champ]
    operateur = filtre.get("operateur")
    if operateur not in dict(OPERATEURS[definition["type"]]):
        raise Erreur_parametres("Filtre '%s' : opérateur non valide." % definition["label"])
    valeur, valeur2 = filtre.get("valeur", ""), filtre.get("valeur2", "")
    if definition["type"] in ("choix", "liste"):
        valeur = [str(v) for v in (valeur if isinstance(valeur, list) else [valeur]) if str(v) != ""]
        if not valeur:
            raise Erreur_parametres("Filtre '%s' : sélectionnez au moins une valeur." % definition["label"])
    if definition["type"] == "nombre" and operateur != "vide":
        try:
            valeur = float(str(valeur).replace(",", "."))
            valeur2 = float(str(valeur2).replace(",", ".")) if operateur == "entre" else None
        except ValueError:
            raise Erreur_parametres("Filtre '%s' : saisissez un nombre." % definition["label"])
    if definition["type"] == "date" and operateur != "vide":
        try:
            valeur = datetime.date.fromisoformat(str(valeur))
            valeur2 = datetime.date.fromisoformat(str(valeur2)) if operateur == "entre" else None
        except ValueError:
            raise Erreur_parametres("Filtre '%s' : saisissez une date valide." % definition["label"])
    if definition["type"] == "texte" and operateur in ("contient", "egal") and not str(valeur).strip():
        raise Erreur_parametres("Filtre '%s' : saisissez un texte." % definition["label"])
    mode = "dont" if filtre.get("mode") == "dont" else "uniquement"
    return {"champ": champ, "type": definition["type"], "operateur": operateur, "valeur": valeur, "valeur2": valeur2, "mode": mode,
            "label": Label_filtre(definition, operateur, valeur, valeur2), "label_court": definition["label"].split(" : ")[-1]}


def Label_filtre(definition={}, operateur="", valeur=None, valeur2=None):
    texte_operateur = dict(OPERATEURS[definition["type"]])[operateur]
    nom = definition["label"].split(" : ")[-1]
    if operateur in ("coche", "non_coche", "vide", "non_vide"):
        return "%s %s" % (nom, texte_operateur)
    if definition["type"] in ("choix", "liste"):
        dict_choix = dict(definition["choix"])
        return "%s %s : %s" % (nom, texte_operateur, ", ".join(dict_choix.get(v, v) for v in valeur))
    def Formater(v):
        if isinstance(v, datetime.date):
            return utils_dates.ConvertDateToFR(v)
        if isinstance(v, float):
            return ("%g" % v).replace(".", ",")
        return str(v)
    if operateur == "entre":
        return "%s %s %s et %s" % (nom, texte_operateur, Formater(valeur), Formater(valeur2))
    return "%s %s %s" % (nom, texte_operateur, Formater(valeur))


# ------------------------------------------------------------------------------------------------------------------
# Filtres de population
# ------------------------------------------------------------------------------------------------------------------

class Filtres_population():
    """ Évalue les filtres de population sur une consommation """
    def __init__(self, filtres=[], date_debut=None, date_fin=None, quotients=None):
        self.filtres = filtres
        self.quotients = quotients
        self.reponses = {}
        for filtre in filtres:
            if filtre["champ"].startswith("question_"):
                categorie, idquestion = filtre["champ"].split("_")[1], int(filtre["champ"].split("_")[2])
                dict_reponses = {}
                for reponse in QuestionnaireReponse.objects.filter(question_id=idquestion).values("individu_id", "famille_id", "reponse"):
                    cle = reponse["individu_id"] if categorie == "individu" else reponse["famille_id"]
                    if cle:
                        dict_reponses[cle] = reponse["reponse"]
                self.reponses[filtre["champ"]] = (categorie, dict_reponses)

    @property
    def uniquement(self):
        return [f for f in self.filtres if f["mode"] == "uniquement"]

    @property
    def dont(self):
        return [f for f in self.filtres if f["mode"] == "dont"]

    def Repondu(self, filtre=None, individu_id=None, famille_id=None):
        categorie, dict_reponses = self.reponses[filtre["champ"]]
        reponse = dict_reponses.get(individu_id if categorie == "individu" else famille_id)
        return reponse not in (None, "")

    def Valide(self, filtre=None, ctx={}):
        champ, operateur, valeur, valeur2 = filtre["champ"], filtre["operateur"], filtre["valeur"], filtre["valeur2"]

        # Récupération de la donnée
        if champ.startswith("question_"):
            categorie, dict_reponses = self.reponses[champ]
            donnee = dict_reponses.get(ctx["individu_id"] if categorie == "individu" else ctx["famille_id"])
        elif champ == "regime":
            donnee = str(ctx["regime_id"] or 0)
        elif champ == "caisse":
            donnee = str(ctx["caisse_id"] or 0)
        elif champ == "age":
            donnee = ctx["age"] if ctx["age"] >= 0 else None
        elif champ == "qf":
            donnee = ctx["qf"]()
        else:
            donnee = None

        type_filtre = filtre["type"]
        if operateur == "vide":
            return donnee in (None, "")
        if operateur == "non_vide":
            return donnee not in (None, "")
        if type_filtre == "coche":
            coche = donnee in ("True", "1", True, 1)
            return coche if operateur == "coche" else not coche
        if type_filtre in ("choix", "liste"):
            valeurs_donnee = set(str(donnee).split(";")) if donnee not in (None, "") else set()
            trouve = bool(valeurs_donnee & set(valeur))
            return trouve if operateur == "parmi" else not trouve
        if donnee in (None, ""):
            return False
        if type_filtre == "texte":
            if operateur == "contient":
                return str(valeur).lower() in str(donnee).lower()
            return str(valeur).strip().lower() == str(donnee).strip().lower()
        if type_filtre == "nombre":
            try:
                donnee = float(str(donnee).replace(",", "."))
            except ValueError:
                return False
        if type_filtre == "date":
            try:
                donnee = datetime.date.fromisoformat(str(donnee)[:10])
            except ValueError:
                return False
        if operateur == "egal":
            return donnee == valeur
        if operateur in ("sup", "apres"):
            return donnee >= valeur
        if operateur in ("inf", "avant"):
            return donnee <= valeur
        if operateur == "entre":
            return valeur <= donnee <= valeur2
        return False


# ------------------------------------------------------------------------------------------------------------------
# Calcul
# ------------------------------------------------------------------------------------------------------------------

class Calcul():
    def __init__(self, parametres={}, request=None):
        self.p = parametres
        self.request = request
        self.erreurs = []
        self.controles = []

    # ---------------------------------------------- Préparation ----------------------------------------------

    def Preparer(self):
        p = self.p
        self.date_debut, self.date_fin = p["date_debut"], p["date_fin"]
        self.colonnes = list(p["colonnes"].keys())
        self.ids_unites = set()
        for colonne in p["colonnes"].values():
            self.ids_unites.update(colonne["unites"].keys())
        self.etats = set()
        for colonne in p["colonnes"].values():
            self.etats.update(colonne["etats"])

        # Régimes, familles (caisse) et individus
        self.dict_regimes = {regime.pk: regime.nom for regime in Regime.objects.all()}
        self.dict_caisses = {caisse.pk: caisse.nom for caisse in Caisse.objects.all()}
        self.dict_familles = {}
        for idfamille, idcaisse, idregime, nom in Famille.objects.values_list("pk", "caisse_id", "caisse__regime_id", "nom"):
            self.dict_familles[idfamille] = {"caisse_id": idcaisse, "regime_id": idregime, "nom": nom}
        self.dict_individus = {}
        for idindividu, nom, prenom, date_naiss in Individu.objects.values_list("pk", "nom", "prenom", "date_naiss"):
            self.dict_individus[idindividu] = {"nom": ("%s %s" % (nom or "", prenom or "")).strip(), "date_naiss": date_naiss}

        # Périodes de vacances (logique identique à l'état global)
        self.liste_vacances = []
        for vacance in Vacance.objects.all().order_by("date_debut"):
            grandes_vacs = vacance.date_debut.month in (6, 7, 8, 9) or vacance.date_fin.month in (6, 7, 8, 9)
            self.liste_vacances.append({"nom": vacance.nom, "annee": vacance.annee, "date_debut": vacance.date_debut, "date_fin": vacance.date_fin, "vacs": True, "grandesVacs": grandes_vacs})
        self.liste_periodes_detail = self.Get_periodes_detaillees()

        # Tranches d'âge (logique identique à l'état global)
        self.dict_tranches_age = {}
        tranches = p["regroupement_age"]
        if tranches:
            for index, borne in enumerate(tranches):
                if index == 0:
                    self.dict_tranches_age[index] = {"label": "Âge < %d ans" % borne, "min": -1, "max": borne}
                else:
                    self.dict_tranches_age[index] = {"label": "Âge >= %d et < %d ans" % (tranches[index - 1], borne), "min": tranches[index - 1], "max": borne}
                self.dict_tranches_age[index + 1] = {"label": "Âge >= %d ans" % borne, "min": borne, "max": -1}

        # Quotients familiaux
        self.dict_quotients = {}
        besoin_qf = "qf" in p["regroupement_principal"] or any(f["champ"] == "qf" for f in p["filtres"])
        if besoin_qf:
            for quotient in Quotient.objects.filter(date_debut__lte=self.date_fin, date_fin__gte=self.date_debut).order_by("date_debut"):
                self.dict_quotients.setdefault(quotient.famille_id, []).append((quotient.date_debut, quotient.date_fin, quotient.quotient))
        self.liste_tranches_qf = []
        if p["regroupement_principal"] == "qf_tarifs":
            for qf_min, qf_max in TarifLigne.objects.filter(qf_min__isnull=False, qf_max__isnull=False, activite__in=p["activites"]).values_list("qf_min", "qf_max"):
                tranche = (int(qf_min), int(qf_max))
                if tranche not in self.liste_tranches_qf:
                    self.liste_tranches_qf.append(tranche)
            self.liste_tranches_qf.sort()
        if p["regroupement_principal"] == "qf_perso":
            precedent = 0
            for borne in p["tranches_qf_perso"]:
                self.liste_tranches_qf.append((precedent, borne - 1))
                precedent = borne
            self.liste_tranches_qf.append((precedent, 999999))

        # Informations individuelles complètes (uniquement si un regroupement en a besoin)
        self.infos_individus, self.infos_familles = {}, {}
        if p["regroupement_principal"] in REGROUPEMENTS_INFOS or p["regroupement_principal"].startswith("question_"):
            from core.utils import utils_infos_individus
            infos = utils_infos_individus.Informations(date_reference=self.date_debut, qf=False, inscriptions=False, messages=False, infosMedicales=False,
                                                       cotisationsManquantes=False, piecesManquantes=False,
                                                       questionnaires=p["regroupement_principal"].startswith("question_"), scolarite=True)
            self.infos_individus = infos.GetDictValeurs(mode="individu", ID=None, formatChamp=False)
            self.infos_familles = infos.GetDictValeurs(mode="famille", ID=None, formatChamp=False)

        # Évènements (pour les regroupements par évènement)
        self.dict_evenements = {}
        if p["regroupement_principal"] in ("evenement", "evenement_date"):
            for evenement in Evenement.objects.filter(date__gte=self.date_debut, date__lte=self.date_fin):
                self.dict_evenements[evenement.pk] = {"nom": evenement.nom, "date": evenement.date}

        # Filtres de population
        self.filtres = Filtres_population(p["filtres"], self.date_debut, self.date_fin)

    def Get_periodes_detaillees(self):
        """ Reprise à l'identique du calcul des périodes détaillées de l'état global """
        LISTE_MOIS = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        noms_vacances = {"Février": "vacances_fevrier", "Pâques": "vacances_paques", "Eté": "vacances_ete", "Toussaint": "vacances_toussaint", "Noël": "vacances_noel"}
        liste_periodes = []
        for index, dict_temp in enumerate(self.liste_vacances):
            dict_temp = dict(dict_temp)
            dict_temp["code"] = noms_vacances.get(dict_temp["nom"], "?") + "_%d" % dict_temp["annee"]
            dict_temp["label"] = "Vacances %s %d" % (dict_temp["nom"], dict_temp["annee"])
            liste_periodes.append(dict_temp)

            if len(self.liste_vacances) > index + 1:
                date_debut_temp = dict_temp["date_fin"] + datetime.timedelta(days=1)
                date_fin_temp = self.liste_vacances[index + 1]["date_debut"] - datetime.timedelta(days=1)
                annee = dict_temp["annee"]
                initiale = dict_temp["nom"][:1]
                nom = {"F": "mercredis_mars_avril", "P": "mercredis_mai_juin", "E": "mercredis_sept_oct", "T": "mercredis_nov_dec", "N": "mercredis_janv_fev"}.get(initiale, "?")
                if initiale == "N":
                    annee += 1
                label = "Hors vacances %s-%s %d" % (LISTE_MOIS[date_debut_temp.month - 1], LISTE_MOIS[date_fin_temp.month - 1], annee)
                liste_periodes.append({"code": nom + "_%d" % annee, "annee": annee, "label": label, "date_debut": date_debut_temp, "date_fin": date_fin_temp, "vacs": False, "grandesVacs": False})
        return liste_periodes

    def Get_liste_periodes(self):
        """ Lignes du tableau dans l'ordre d'affichage """
        mode = self.p["ventilation_periodes"]
        if mode == "detaillees":
            return [{"code": d["code"], "label": d["label"], "date_debut": d["date_debut"], "date_fin": d["date_fin"]} for d in self.liste_periodes_detail]
        if mode == "mercredis":
            return [{"code": "mercredis", "label": "Mercredis (hors vacances)"}, {"code": "periscolaire", "label": "Autres jours hors vacances"},
                    {"code": "petitesVacs", "label": "Petites vacances"}, {"code": "grandesVacs", "label": "Vacances d'été"}]
        return [{"code": "petitesVacs", "label": "Petites vacances"}, {"code": "grandesVacs", "label": "Vacances d'été"}, {"code": "horsVacs", "label": "Hors vacances"}]

    def Get_periode(self, date=None):
        """ Retourne (code_periode, est_vacances) ou (None, None) si la date n'est couverte par aucune période """
        if self.p["ventilation_periodes"] == "detaillees":
            periode = None
            for dict_periode in self.liste_periodes_detail:
                if dict_periode["date_debut"] <= date <= dict_periode["date_fin"]:
                    periode = dict_periode
            if not periode:
                return None, None
            return periode["code"], periode["vacs"]
        periode = None
        for dict_vac in self.liste_vacances:
            if dict_vac["date_debut"] <= date <= dict_vac["date_fin"]:
                periode = "grandesVacs" if dict_vac["grandesVacs"] else "petitesVacs"
        if periode:
            return periode, True
        if self.p["ventilation_periodes"] == "mercredis":
            return ("mercredis" if date.weekday() == 2 else "periscolaire"), False
        return "horsVacs", False

    def Get_qf(self, idfamille=None, date=None):
        for date_debut, date_fin, quotient in self.dict_quotients.get(idfamille, []):
            if date_debut <= date <= date_fin:
                return quotient
        return None

    # ---------------------------------------------- Valeur d'une consommation ----------------------------------------------

    def Calculer_valeur(self, conso=None, parametres={}, prestations_traitees=None, dict_unites_formule=None):
        """ Durée retenue pour une consommation selon les paramètres de l'unité (règles de l'état global) """
        type_calcul = parametres["type"]
        heure_debut, heure_fin = conso.heure_debut, conso.heure_fin

        if type_calcul == "0":
            return parametres["coeff_delta"]

        if type_calcul == "1":
            if not heure_debut or not heure_fin:
                return ZERO
            if parametres["heure_seuil"]:
                heure_seuil = utils_dates.HeureStrEnTime(parametres["heure_seuil"])
                if heure_debut < heure_seuil:
                    heure_debut = heure_seuil
            if parametres["heure_plafond"]:
                heure_plafond = utils_dates.HeureStrEnTime(parametres["heure_plafond"])
                if heure_fin > heure_plafond:
                    heure_fin = heure_plafond
            valeur = datetime.timedelta(hours=heure_fin.hour, minutes=heure_fin.minute) - datetime.timedelta(hours=heure_debut.hour, minutes=heure_debut.minute)
            if parametres["arrondi"]:
                arrondi_type, arrondi_delta = parametres["arrondi"].split(";")
                valeur = utils_dates.CalculerArrondi(arrondi_type=arrondi_type, arrondi_delta=int(arrondi_delta), heure_debut=heure_debut, heure_fin=heure_fin)
            if parametres["duree_seuil"]:
                duree_seuil = utils_dates.HeureStrEnDelta(parametres["duree_seuil"])
                if valeur < duree_seuil:
                    valeur = duree_seuil
            if parametres["duree_plafond"]:
                duree_plafond = utils_dates.HeureStrEnDelta(parametres["duree_plafond"])
                if valeur > duree_plafond:
                    valeur = duree_plafond
            return valeur

        if type_calcul == "2":
            if conso.prestation_id and conso.prestation.temps_facture not in (None, ""):
                if prestations_traitees is None:
                    return conso.prestation.temps_facture
                if conso.prestation_id not in prestations_traitees:
                    prestations_traitees.add(conso.prestation_id)
                    return conso.prestation.temps_facture
            return ZERO

        if type_calcul == "3":
            debut, fin = utils_dates.TimeEnDelta(heure_debut), utils_dates.TimeEnDelta(heure_fin)
            variables = {"debut": debut, "fin": fin, "duree": fin - debut, "date": conso.date}
            formule = parametres["formule_compilee"]
            for idunite in formule.unites:
                variables["unite%d" % idunite] = (dict_unites_formule or {}).get((conso.date, conso.inscription_id, idunite), Unite_conso())
            try:
                return formule.Calculer(variables)
            except Erreur_parametres:
                raise
            except Exception as err:
                raise Erreur_parametres("La formule saisie pour l'unité %s ne semble pas valide : %s" % (conso.unite.nom, err))

        if type_calcul == "4":
            valeur = ZERO
            if conso.unite.equiv_heures:
                valeur = utils_dates.TimeEnDelta(conso.unite.equiv_heures)
            if conso.evenement_id and conso.evenement.equiv_heures:
                valeur = utils_dates.TimeEnDelta(conso.evenement.equiv_heures)
            return valeur

        return ZERO

    # ---------------------------------------------- Regroupement principal ----------------------------------------------

    def Get_regroupement(self, conso=None, idfamille=None, age=-1):
        code = self.p["regroupement_principal"]
        ii = self.infos_individus.get(conso.individu_id, {})
        ifa = self.infos_familles.get(idfamille, {})
        try:
            if code == "aucun": return None
            if code == "jour": return conso.date
            if code == "mois": return (conso.date.year, conso.date.month)
            if code == "annee": return conso.date.year
            if code == "activite": return conso.activite.nom
            if code == "groupe": return conso.groupe.nom if conso.groupe_id else None
            if code in ("evenement", "evenement_date"): return conso.evenement_id
            if code == "categorie_tarif": return conso.categorie_tarif.nom if conso.categorie_tarif_id else None
            if code == "unite_conso": return conso.unite.nom
            if code == "ville_residence": return ii.get("INDIVIDU_VILLE") or ""
            if code == "secteur": return ii.get("INDIVIDU_SECTEUR")
            if code == "genre": return ii.get("INDIVIDU_SEXE")
            if code == "age": return age if age >= 0 else None
            if code == "ville_naissance": return ii.get("INDIVIDU_VILLE_NAISS")
            if code == "nom_ecole": return ii.get("SCOLARITE_NOM_ECOLE")
            if code == "nom_classe": return ii.get("SCOLARITE_NOM_CLASSE")
            if code == "nom_niveau_scolaire": return ii.get("SCOLARITE_NOM_NIVEAU")
            if code == "famille": return ifa.get("FAMILLE_NOM") or self.dict_familles.get(idfamille, {}).get("nom")
            if code == "individu": return ii.get("INDIVIDU_NOM_COMPLET") or self.dict_individus[conso.individu_id]["nom"]
            if code == "regime":
                return self.dict_regimes.get(self.dict_familles.get(idfamille, {}).get("regime_id"))
            if code == "caisse":
                return self.dict_caisses.get(self.dict_familles.get(idfamille, {}).get("caisse_id"))
            if code == "categorie_travail": return ii.get("INDIVIDU_CATEGORIE_TRAVAIL")
            if code == "categorie_travail_pere": return ii.get("PERE_CATEGORIE_TRAVAIL")
            if code == "categorie_travail_mere": return ii.get("MERE_CATEGORIE_TRAVAIL")
            if code == "qf_100":
                qf = self.Get_qf(idfamille, conso.date)
                if qf:
                    for x in range(0, 10000, 100):
                        if x <= qf <= x + 99:
                            return (x, x + 99)
                return (0, 0)
            if code in ("qf_tarifs", "qf_perso"):
                qf = self.Get_qf(idfamille, conso.date)
                if qf:
                    for qf_min, qf_max in self.liste_tranches_qf:
                        if qf_min <= qf <= qf_max:
                            return (qf_min, qf_max)
                return (0, 0)
            if code.startswith("question_famille_"):
                return ifa.get("QUESTION_%s" % code[17:])
            if code.startswith("question_individu_"):
                return ii.get("QUESTION_%s" % code[18:])
        except Exception:
            return None
        return None

    def Get_label_regroupement(self, regroupement=None):
        code = self.p["regroupement_principal"]
        if code == "aucun":
            return ""
        if regroupement in (None, ""):
            return "- Non renseigné -"
        if code == "jour":
            return utils_dates.ConvertDateToFR(regroupement)
        if code == "mois":
            return utils_dates.FormateMois(regroupement)
        if code == "evenement" and regroupement in self.dict_evenements:
            return self.dict_evenements[regroupement]["nom"]
        if code == "evenement_date" and regroupement in self.dict_evenements:
            return "%s (%s)" % (self.dict_evenements[regroupement]["nom"], utils_dates.ConvertDateToFR(self.dict_evenements[regroupement]["date"]))
        if code.startswith("qf") and isinstance(regroupement, tuple):
            return "Non renseigné" if regroupement == (0, 0) else "%d-%d" % regroupement
        if code == "age":
            return "%d ans" % regroupement
        return str(regroupement)

    def Get_tranche_age(self, age=-1):
        if not self.dict_tranches_age:
            return 0
        if age == -1:
            return None
        index_tranche = 0
        for key, dict_temp in self.dict_tranches_age.items():
            if dict_temp["min"] == -1 and age < dict_temp["max"]: index_tranche = key
            if dict_temp["max"] == -1 and age >= dict_temp["min"]: index_tranche = key
            if dict_temp["min"] != -1 and dict_temp["max"] != -1 and dict_temp["min"] <= age < dict_temp["max"]: index_tranche = key
        return index_tranche

    # ---------------------------------------------- Calcul principal ----------------------------------------------

    def Get_consommations(self, etats=None, avec_select=True):
        consos = Consommation.objects.filter(date__gte=self.date_debut, date__lte=self.date_fin, activite__in=self.p["activites"], unite_id__in=self.ids_unites,
                                             etat__in=etats or self.etats)
        if avec_select:
            consos = consos.select_related("unite", "activite", "groupe", "prestation", "categorie_tarif", "inscription", "evenement")
        return consos.order_by("date", "individu_id", "unite__ordre", "heure_debut")

    def Calculer(self):
        try:
            self.Preparer()
            return self._Calculer()
        except Erreur_parametres as err:
            self.erreurs.append(str(err))
            return None

    def _Calculer(self):
        p = self.p
        aujourdhui = datetime.date.today()
        consos = list(self.Get_consommations())

        # Données des unités pour les formules (toutes les consommations des activités, comme l'état global)
        dict_unites_formule = {}
        if any(u["type"] == "3" for c in p["colonnes"].values() for u in c["unites"].values()):
            for conso in Consommation.objects.filter(date__gte=self.date_debut, date__lte=self.date_fin, activite__in=p["activites"]).only(
                    "date", "inscription_id", "unite_id", "heure_debut", "heure_fin", "etat", "quantite"):
                dict_unites_formule[(conso.date, conso.inscription_id, conso.unite_id)] = Unite_conso(conso.unite_id, conso.heure_debut, conso.heure_fin, conso.etat, conso.quantite)

        resultats = {colonne: {} for colonne in self.colonnes}
        resultats_dont = {colonne: {} for colonne in self.colonnes}
        mois = {colonne: {} for colonne in self.colonnes}
        stats = {colonne: {"individus": set(), "familles": set(), "journees": set(), "total": ZERO} for colonne in self.colonnes}
        stats_dont = [{colonne: {"individus": set(), "total": ZERO} for colonne in self.colonnes} for filtre in self.filtres.dont]
        prestations_traitees = {colonne: set() for colonne in self.colonnes}
        temps_journalier = {colonne: {} for colonne in self.colonnes}
        regimes_utilises = set()
        exclus_filtre = set()
        retenus_filtre = set()
        dates_sans_periode = set()
        anomalies = {"sans_heures": [], "sans_temps_facture": [], "reservations_passees": [], "equiv_manquante": set(),
                     "sans_date_naiss": {}, "sans_regime": {}, "plafonnes": 0, "sans_reponse": {}}

        for conso in consos:
            idfamille = conso.inscription.famille_id
            infos_famille = self.dict_familles.get(idfamille, {})
            age = Age(self.dict_individus.get(conso.individu_id, {}).get("date_naiss"), conso.date)
            ctx = {"individu_id": conso.individu_id, "famille_id": idfamille, "regime_id": infos_famille.get("regime_id"),
                   "caisse_id": infos_famille.get("caisse_id"), "age": age, "qf": lambda: self.Get_qf(idfamille, conso.date)}

            # Filtres de population "uniquement"
            valide_population = True
            for filtre in self.filtres.uniquement:
                if filtre["champ"].startswith("question_") and not self.filtres.Repondu(filtre, conso.individu_id, idfamille):
                    anomalies["sans_reponse"].setdefault(filtre["label_court"], {})[conso.individu_id] = idfamille
                if not self.filtres.Valide(filtre, ctx):
                    valide_population = False
            if not valide_population:
                exclus_filtre.add(conso.individu_id)
                continue
            retenus_filtre.add(conso.individu_id)

            # Période
            periode, est_vacances = self.Get_periode(conso.date)
            if periode is None:
                dates_sans_periode.add(conso.date)
                continue

            # Jours
            jours = p["jours_vacances"] if est_vacances else p["jours_hors_vacances"]
            if str(conso.date.weekday()) not in jours:
                continue

            regroupement = None
            tranche_age = self.Get_tranche_age(age)
            filtres_dont_valides = [index for index, filtre in enumerate(self.filtres.dont) if self.filtres.Valide(filtre, ctx)]

            for code_colonne in self.colonnes:
                colonne = p["colonnes"][code_colonne]
                parametres = colonne["unites"].get(conso.unite_id)
                if not parametres or conso.etat not in colonne["etats"]:
                    continue

                # Anomalies
                if parametres["type"] in ("1", "3") and (not conso.heure_debut or not conso.heure_fin):
                    anomalies["sans_heures"].append(conso)
                if parametres["type"] == "2" and (not conso.prestation_id or conso.prestation.temps_facture in (None, "")):
                    anomalies["sans_temps_facture"].append(conso)
                if parametres["type"] == "4" and not conso.unite.equiv_heures and not (conso.evenement_id and conso.evenement.equiv_heures):
                    anomalies["equiv_manquante"].add(conso.unite.nom)
                if conso.etat == "reservation" and conso.date < aujourdhui:
                    anomalies["reservations_passees"].append(conso)

                valeur = self.Calculer_valeur(conso, parametres, prestations_traitees[code_colonne], dict_unites_formule)

                # Plafond journalier par individu (toutes activités confondues)
                if p["plafond_journalier"] > 0:
                    plafond = datetime.timedelta(minutes=p["plafond_journalier"])
                    deja = temps_journalier[code_colonne].get((conso.individu_id, conso.date), ZERO)
                    if deja + valeur > plafond:
                        valeur = plafond - deja
                        anomalies["plafonnes"] += 1
                    temps_journalier[code_colonne][(conso.individu_id, conso.date)] = deja + valeur

                if valeur == ZERO:
                    continue

                # Régime
                regime = infos_famille.get("regime_id") or 0
                if regime == 0:
                    anomalies["sans_regime"][idfamille] = conso.individu_id
                    if p["associer_regime_inconnu"]:
                        regime = p["associer_regime_inconnu"]
                regimes_utilises.add(regime)

                if tranche_age is None:
                    anomalies["sans_date_naiss"][conso.individu_id] = idfamille

                if regroupement is None:
                    regroupement = self.Get_regroupement(conso, idfamille, age)
                    if isinstance(regroupement, datetime.date):
                        regroupement = str(regroupement)
                    regroupement = ("__valeur__", regroupement)

                quantite = conso.quantite if conso.quantite else 1
                valeur = valeur * quantite

                # Mémorisation
                niveau = resultats[code_colonne].setdefault(regroupement, {}).setdefault(tranche_age, {}).setdefault(periode, {})
                niveau[regime] = niveau.get(regime, ZERO) + valeur
                cle_mois = (conso.date.year, conso.date.month)
                mois[code_colonne][cle_mois] = mois[code_colonne].get(cle_mois, ZERO) + valeur
                stats_colonne = stats[code_colonne]
                stats_colonne["individus"].add(conso.individu_id)
                stats_colonne["familles"].add(idfamille)
                stats_colonne["journees"].add((conso.individu_id, conso.date))
                stats_colonne["total"] += valeur
                for index in filtres_dont_valides:
                    niveau_dont = resultats_dont[code_colonne].setdefault(regroupement, {})
                    niveau_dont[index] = niveau_dont.get(index, ZERO) + valeur
                    stats_dont[index][code_colonne]["individus"].add(conso.individu_id)
                    stats_dont[index][code_colonne]["total"] += valeur

        if dates_sans_periode:
            self.erreurs.append("Période inconnue pour %d date(s), dont le %s. Vérifiez que les périodes de vacances ont bien été paramétrées dans Paramétrage > Vacances." % (
                len(dates_sans_periode), utils_dates.ConvertDateToFR(min(dates_sans_periode))))
            return None

        self.Creer_controles(anomalies, exclus_filtre)
        return self.Mettre_en_forme(resultats, resultats_dont, mois, stats, stats_dont, regimes_utilises, retenus_filtre, exclus_filtre)

    # ---------------------------------------------- Contrôles qualité ----------------------------------------------

    def Lien_individu(self, idindividu=None, idfamille=None):
        try:
            return reverse("individu_resume", args=[idfamille, idindividu])
        except Exception:
            return None

    def Lien_famille(self, idfamille=None):
        try:
            return reverse("famille_resume", args=[idfamille])
        except Exception:
            return None

    def Creer_controles(self, anomalies={}, exclus_filtre=set()):
        def Details_consos(liste):
            details = []
            for conso in liste[:100]:
                details.append({"label": "%s - %s - %s" % (self.dict_individus.get(conso.individu_id, {}).get("nom", "?"), utils_dates.ConvertDateToFR(conso.date), conso.unite.nom),
                                "lien": self.Lien_individu(conso.individu_id, conso.inscription.famille_id)})
            return details

        def Ajouter(niveau="warning", message="", details=[], lien=None, libelle_lien=None, nombre=0):
            self.controles.append({"niveau": niveau, "message": message, "details": details, "lien": lien, "libelle_lien": libelle_lien,
                                   "nombre": nombre, "nombre_details_masques": max(0, nombre - len(details))})

        if anomalies["reservations_passees"]:
            nbre = len({c.pk for c in anomalies["reservations_passees"]})
            lien = None
            try:
                lien = reverse("suivi_pointage")
            except Exception:
                pass
            Ajouter("warning", "%d consommation(s) encore à l'état Réservation sur des dates passées. Elles comptent dans les colonnes où l'état Réservation est coché." % nbre,
                    Details_consos(anomalies["reservations_passees"]), lien=lien, libelle_lien="Ouvrir le suivi du pointage", nombre=nbre)

        if anomalies["sans_heures"]:
            nbre = len({c.pk for c in anomalies["sans_heures"]})
            Ajouter("warning", "%d consommation(s) sans heure de début ou de fin : leur temps réel ne peut pas être calculé (0 h retenue)." % nbre,
                    Details_consos(anomalies["sans_heures"]), nombre=nbre)

        if anomalies["sans_temps_facture"]:
            nbre = len({c.pk for c in anomalies["sans_temps_facture"]})
            Ajouter("warning", "%d consommation(s) sans prestation ou sans temps facturé paramétré dans le tarif (0 h retenue)." % nbre,
                    Details_consos(anomalies["sans_temps_facture"]), nombre=nbre)

        if anomalies["equiv_manquante"]:
            noms = sorted(anomalies["equiv_manquante"])
            Ajouter("danger", "Aucune équivalence en heures n'est paramétrée pour : %s (0 h retenue). Renseignez-la dans le paramétrage de l'unité ou choisissez une autre méthode." % ", ".join(noms),
                    nombre=len(noms))

        if anomalies["sans_date_naiss"] and self.dict_tranches_age:
            details = [{"label": self.dict_individus.get(idindividu, {}).get("nom", "?"), "lien": self.Lien_individu(idindividu, idfamille)}
                       for idindividu, idfamille in list(anomalies["sans_date_naiss"].items())[:100]]
            Ajouter("warning", "%d individu(s) sans date de naissance : ils apparaissent dans une ligne « Sans date de naissance »." % len(anomalies["sans_date_naiss"]),
                    sorted(details, key=lambda d: d["label"]), nombre=len(anomalies["sans_date_naiss"]))

        if anomalies["sans_regime"] and (self.p["regroupement_regime"] or self.p["regroupement_principal"] in ("regime", "caisse")):
            details = [{"label": self.dict_familles.get(idfamille, {}).get("nom") or "Famille %d" % idfamille, "lien": self.Lien_famille(idfamille)}
                       for idfamille in list(anomalies["sans_regime"].keys())[:100]]
            suite = "elles sont rattachées au régime « %s »." % self.dict_regimes.get(self.p["associer_regime_inconnu"]) if self.p["associer_regime_inconnu"] else "elles apparaissent dans la colonne « Sans régime »."
            Ajouter("warning", "%d famille(s) sans caisse ou régime renseigné : %s" % (len(anomalies["sans_regime"]), suite),
                    sorted(details, key=lambda d: d["label"]), nombre=len(anomalies["sans_regime"]))

        for label_question, dict_individus in anomalies["sans_reponse"].items():
            details = [{"label": self.dict_individus.get(idindividu, {}).get("nom", "?"), "lien": self.Lien_individu(idindividu, idfamille)}
                       for idindividu, idfamille in list(dict_individus.items())[:100]]
            Ajouter("info", "%d individu(s) n'ont jamais répondu à la question « %s » du filtre." % (len(dict_individus), label_question),
                    sorted(details, key=lambda d: d["label"]), nombre=len(dict_individus))

        if anomalies["plafonnes"]:
            Ajouter("info", "Le plafond journalier a réduit le temps retenu sur %d consommation(s)." % anomalies["plafonnes"], nombre=anomalies["plafonnes"])

    # ---------------------------------------------- Mise en forme ----------------------------------------------

    def Mettre_en_forme(self, resultats={}, resultats_dont={}, mois={}, stats={}, stats_dont=[], regimes_utilises=set(), retenus_filtre=set(), exclus_filtre=set()):
        p = self.p
        colonnes = [(code, p["colonnes"][code]["label"]) for code in self.colonnes]
        regimes = sorted(regimes_utilises, key=lambda idregime: (idregime == 0, self.dict_regimes.get(idregime, "")))
        regimes = [(idregime, self.dict_regimes.get(idregime, "Sans régime")) for idregime in regimes]
        liste_periodes = self.Get_liste_periodes()

        def Valeurs(dict_regimes={}):
            """ dict {idregime: td} -> {"regimes": [td...], "total": td} """
            valeurs = [dict_regimes.get(idregime, ZERO) for idregime, nom in regimes]
            return {"regimes": valeurs, "total": sum(valeurs, ZERO)}

        def Additionner(cumul, valeurs):
            cumul["regimes"] = [a + b for a, b in zip(cumul["regimes"], valeurs["regimes"])]
            cumul["total"] += valeurs["total"]

        def Vide():
            return {"regimes": [ZERO for r in regimes], "total": ZERO}

        # Tous les regroupements présents dans au moins une colonne
        cles = set()
        for code in self.colonnes:
            cles.update(resultats[code].keys())

        def Cle_tri(cle):
            valeur = cle[1]
            return (valeur is None, str(type(valeur)), valeur if valeur is not None else "")

        tableaux = []
        for cle in sorted(cles, key=Cle_tri):
            regroupement = cle[1]
            tranches = set()
            for code in self.colonnes:
                tranches.update(resultats[code].get(cle, {}).keys())
            blocs = []
            total_tableau = {code: Vide() for code in self.colonnes}
            for tranche in sorted(tranches, key=lambda t: (t is None, t if t is not None else 0)):
                if tranche is None:
                    label_tranche = "Sans date de naissance"
                else:
                    label_tranche = self.dict_tranches_age.get(tranche, {}).get("label", "")
                lignes = []
                total_bloc = {code: Vide() for code in self.colonnes}
                for dict_periode in liste_periodes:
                    presente = any(dict_periode["code"] in resultats[code].get(cle, {}).get(tranche, {}) for code in self.colonnes)
                    if not presente:
                        continue
                    detail = ""
                    if "date_debut" in dict_periode:
                        detail = "Du %s au %s" % (utils_dates.ConvertDateToFR(max(dict_periode["date_debut"], self.date_debut)),
                                                  utils_dates.ConvertDateToFR(min(dict_periode["date_fin"], self.date_fin)))
                    valeurs = {}
                    for code in self.colonnes:
                        valeurs[code] = Valeurs(resultats[code].get(cle, {}).get(tranche, {}).get(dict_periode["code"], {}))
                        Additionner(total_bloc[code], valeurs[code])
                    lignes.append({"label": dict_periode["label"], "detail": detail, "valeurs": valeurs})
                for code in self.colonnes:
                    Additionner(total_tableau[code], total_bloc[code])
                blocs.append({"label": label_tranche, "lignes": lignes, "total": total_bloc})

            dont = []
            for index, filtre in enumerate(self.filtres.dont):
                dont.append({"label": "dont %s" % filtre["label"],
                             "valeurs": {code: resultats_dont[code].get(cle, {}).get(index, ZERO) for code in self.colonnes}})

            tableaux.append({"label": self.Get_label_regroupement(regroupement), "blocs": blocs, "total": total_tableau, "dont": dont,
                             "multi_blocs": len(blocs) > 1 or any(b["label"] for b in blocs)})

        # Total général (utile quand il y a un regroupement principal)
        total_general = {code: Vide() for code in self.colonnes}
        for tableau in tableaux:
            for code in self.colonnes:
                Additionner(total_general[code], tableau["total"][code])

        # Indicateurs clés
        tous_individus, toutes_familles = set(), set()
        for code in self.colonnes:
            tous_individus |= stats[code]["individus"]
            toutes_familles |= stats[code]["familles"]
        colonne_ref = "realise" if "realise" in self.colonnes else self.colonnes[0]
        kpi = {
            "totaux": {code: stats[code]["total"] for code in self.colonnes},
            "individus": len(tous_individus),
            "familles": len(toutes_familles),
            "journees": len(stats[colonne_ref]["journees"]),
            "colonne_journees": p["colonnes"][colonne_ref]["label"].lower(),
            "taux": None,
            "dont": [{"label": f["label"], "individus": len(set().union(*[stats_dont[i][c]["individus"] for c in self.colonnes])),
                      "totaux": {c: stats_dont[i][c]["total"] for c in self.colonnes}} for i, f in enumerate(self.filtres.dont)],
        }
        if "realise" in self.colonnes and "facture" in self.colonnes and stats["facture"]["total"]:
            kpi["taux"] = round(100.0 * stats["realise"]["total"].total_seconds() / stats["facture"]["total"].total_seconds(), 1)

        # Données mensuelles pour le graphique
        liste_mois, annee, num_mois = [], self.date_debut.year, self.date_debut.month
        while (annee, num_mois) <= (self.date_fin.year, self.date_fin.month):
            liste_mois.append((annee, num_mois))
            num_mois += 1
            if num_mois > 12:
                annee, num_mois = annee + 1, 1
        graphe = {"labels": ["%s %d" % (utils_dates.LISTE_MOIS_ABREGES[m - 1], a) for a, m in liste_mois],
                  "series": [{"code": code, "label": label, "label_heures": LABELS_HEURES[code], "valeurs": [Heures(mois[code].get(cle_mois)) for cle_mois in liste_mois]} for code, label in colonnes]}

        # Cellules formatées dans l'ordre d'affichage (régimes x colonnes, puis totaux par colonne)
        format_donnees = p["format_donnees"]
        avec_regimes = p["regroupement_regime"]

        def Cellules(valeurs_colonnes):
            cellules = []
            if avec_regimes:
                for index_regime in range(len(regimes)):
                    for code in self.colonnes:
                        cellules.append(Formater_duree(valeurs_colonnes[code]["regimes"][index_regime], format_donnees))
            for code in self.colonnes:
                cellules.append(Formater_duree(valeurs_colonnes[code]["total"], format_donnees))
            return cellules

        for tableau in tableaux:
            for bloc in tableau["blocs"]:
                for ligne in bloc["lignes"]:
                    ligne["cellules"] = Cellules(ligne["valeurs"])
                bloc["cellules_total"] = Cellules(bloc["total"])
            tableau["cellules_total"] = Cellules(tableau["total"])
            for dont in tableau["dont"]:
                dont["cellules"] = [""] * (len(regimes) * len(self.colonnes) if avec_regimes else 0) + [Formater_duree(dont["valeurs"][code], format_donnees) for code in self.colonnes]
        entetes = []
        if avec_regimes:
            for idregime, nom_regime in regimes:
                for code, label in colonnes:
                    entetes.append({"haut": nom_regime, "bas": label, "total": False})
        for code, label in colonnes:
            entetes.append({"haut": "Total", "bas": label, "total": True})
        kpi["totaux_str"] = [{"code": code, "label": label, "label_heures": LABELS_HEURES[code], "valeur": Formater_duree(kpi["totaux"][code], format_donnees)} for code, label in colonnes]
        for dont in kpi["dont"]:
            dont["totaux_str"] = [{"label": label, "valeur": Formater_duree(dont["totaux"][code], format_donnees)} for code, label in colonnes]

        return {
            "entetes": entetes,
            "cellules_total_general": Cellules(total_general),
            "colonnes": colonnes,
            "regimes": regimes,
            "regroupement_regime": p["regroupement_regime"],
            "regroupement_principal": p["regroupement_principal"],
            "tableaux": tableaux,
            "total_general": total_general,
            "kpi": kpi,
            "graphe": graphe,
            "controles": self.controles,
            "population": {"retenus": len(retenus_filtre), "exclus": len(exclus_filtre - retenus_filtre)},
            "format": p["format_donnees"],
        }

    # ---------------------------------------------- Résumé des paramètres ----------------------------------------------

    def Get_resume_parametres(self):
        """ Lignes de rappel des paramètres (en-tête des exports) """
        p = self.p
        noms_jours = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
        lignes = [
            ("Période", "Du %s au %s" % (utils_dates.ConvertDateToFR(p["date_debut"]), utils_dates.ConvertDateToFR(p["date_fin"]))),
            ("Activités", ", ".join(activite.nom for activite in p["activites"])),
        ]
        for code, colonne in p["colonnes"].items():
            lignes.append(("États retenus (%s)" % colonne["label"].lower(), ", ".join(dict(ETATS)[e] for e in colonne["etats"])))
        if len(p["jours_hors_vacances"]) != 7:
            lignes.append(("Jours hors vacances", ", ".join(noms_jours[int(j)] for j in p["jours_hors_vacances"]) or "aucun"))
        if len(p["jours_vacances"]) != 7:
            lignes.append(("Jours de vacances", ", ".join(noms_jours[int(j)] for j in p["jours_vacances"]) or "aucun"))
        for filtre in p["filtres"]:
            lignes.append(("Filtre" if filtre["mode"] == "uniquement" else "Sous-total", filtre["label"]))
        if p["plafond_journalier"]:
            lignes.append(("Plafond journalier", Formater_duree(datetime.timedelta(minutes=p["plafond_journalier"]), "horaire")))
        return lignes


# ------------------------------------------------------------------------------------------------------------------
# Comptage de la population (compteur dynamique de l'étape "Qui compter ?")
# ------------------------------------------------------------------------------------------------------------------

def Compter_population(parametres={}):
    calcul = Calcul(parametres)
    calcul.date_debut, calcul.date_fin = parametres["date_debut"], parametres["date_fin"]
    calcul.p = parametres
    calcul.ids_unites = set()
    calcul.etats = set()
    for colonne in parametres["colonnes"].values():
        calcul.ids_unites.update(colonne["unites"].keys())
        calcul.etats.update(colonne["etats"])
    dict_familles = {idfamille: {"caisse_id": idcaisse, "regime_id": idregime} for idfamille, idcaisse, idregime in Famille.objects.values_list("pk", "caisse_id", "caisse__regime_id")}
    dict_naiss = dict(Individu.objects.values_list("pk", "date_naiss"))
    calcul.dict_quotients = {}
    if any(f["champ"] == "qf" for f in parametres["filtres"]):
        for quotient in Quotient.objects.filter(date_debut__lte=calcul.date_fin, date_fin__gte=calcul.date_debut):
            calcul.dict_quotients.setdefault(quotient.famille_id, []).append((quotient.date_debut, quotient.date_fin, quotient.quotient))
    filtres = Filtres_population(parametres["filtres"], calcul.date_debut, calcul.date_fin)

    tous, retenus, sans_reponse = set(), set(), {}
    for idindividu, idfamille, date in calcul.Get_consommations(avec_select=False).values_list("individu_id", "inscription__famille_id", "date").distinct():
        tous.add(idindividu)
        if idindividu in retenus:
            continue
        infos = dict_familles.get(idfamille, {})
        ctx = {"individu_id": idindividu, "famille_id": idfamille, "regime_id": infos.get("regime_id"), "caisse_id": infos.get("caisse_id"),
               "age": Age(dict_naiss.get(idindividu), date), "qf": lambda: calcul.Get_qf(idfamille, date)}
        valide = True
        for filtre in filtres.uniquement:
            if filtre["champ"].startswith("question_") and not filtres.Repondu(filtre, idindividu, idfamille):
                sans_reponse.setdefault(filtre["label_court"], set()).add(idindividu)
            if not filtres.Valide(filtre, ctx):
                valide = False
        if valide:
            retenus.add(idindividu)
    return {"tous": len(tous), "retenus": len(retenus), "sans_reponse": [{"question": q, "nombre": len(s)} for q, s in sans_reponse.items()]}


# ------------------------------------------------------------------------------------------------------------------
# Exemple de calcul pour une unité (aperçu sous la méthode choisie)
# ------------------------------------------------------------------------------------------------------------------

def Get_exemple(parametres_unite={}, idunite=None, date_debut=None, date_fin=None, etats=None):
    consos = Consommation.objects.select_related("unite", "prestation", "evenement", "individu", "inscription").filter(
        unite_id=idunite, date__gte=date_debut, date__lte=date_fin, etat__in=etats or ["present"])
    type_calcul = parametres_unite["type"]
    if type_calcul in ("1", "3"):
        consos = consos.filter(heure_debut__isnull=False, heure_fin__isnull=False)
    if type_calcul == "2":
        consos = consos.filter(prestation__temps_facture__isnull=False)
    conso = consos.order_by("-date").first()
    if not conso:
        return {"texte": "Aucune consommation de cette unité sur la période pour illustrer le calcul."}

    calcul = Calcul({})
    dict_unites_formule = {}
    if type_calcul == "3":
        for autre in Consommation.objects.filter(date=conso.date, inscription_id=conso.inscription_id):
            dict_unites_formule[(autre.date, autre.inscription_id, autre.unite_id)] = Unite_conso(autre.unite_id, autre.heure_debut, autre.heure_fin, autre.etat, autre.quantite)
    valeur = calcul.Calculer_valeur(conso, parametres_unite, None, dict_unites_formule) * (conso.quantite or 1)

    nom = conso.individu.Get_nom() if hasattr(conso.individu, "Get_nom") else str(conso.individu)
    date_texte = utils_dates.DateComplete(conso.date)
    debut = "%s, %s" % (nom, date_texte[:1].lower() + date_texte[1:])
    if type_calcul == "1":
        duree_reelle = utils_dates.TimeEnDelta(conso.heure_fin) - utils_dates.TimeEnDelta(conso.heure_debut)
        explication = "présent de %s à %s, soit %s" % (conso.heure_debut.strftime("%Hh%M"), conso.heure_fin.strftime("%Hh%M"), Formater_duree(duree_reelle, "horaire"))
    elif type_calcul == "2":
        explication = "temps facturé de la prestation « %s »" % (conso.prestation.label or "")
    elif type_calcul == "4":
        explication = "équivalence de l'unité %s" % conso.unite.nom
    elif type_calcul == "0":
        explication = "%d unité(s) × %s" % (conso.quantite or 1, Formater_duree(parametres_unite["coeff_delta"], "horaire"))
    else:
        explication = "résultat de la formule"
    return {"texte": "%s : %s → %s retenue(s)" % (debut, explication, Formater_duree(valeur, "horaire")), "valeur": Formater_duree(valeur, "horaire")}


# ------------------------------------------------------------------------------------------------------------------
# Conversion d'un profil de l'état global
# ------------------------------------------------------------------------------------------------------------------

def Convertir_profil_etat_global(donnees={}):
    """ Transforme un profil de l'état global en paramètres de l'assistant (la colonne Réalisé reprend le profil) """
    options = donnees.get("options", {})
    parametres = donnees.get("parametres", {})
    etats = [e for e in options.get("etat_consommations", []) if e in dict(ETATS)] or ["present"]
    unites = {}
    for idunite, dict_unite in parametres.items():
        if not str(idunite).isdigit():
            continue
        unites[str(idunite)] = {cle: dict_unite.get(cle, "") or "" for cle in ("type", "coeff", "formule", "arrondi", "duree_seuil", "duree_plafond", "heure_seuil", "heure_plafond")}
    plafond = options.get("plafond_journalier_individu") or 0
    associer = options.get("associer_regime_inconnu")
    return {
        "jours_hors_vacances": [str(j) for j in options.get("jours_hors_vacances", JOURS_TOUS)],
        "jours_vacances": [str(j) for j in options.get("jours_vacances", JOURS_TOUS)],
        "colonnes": {
            "realise": {"active": True, "etats": etats, "unites": unites},
            "facture": {"active": False, "etats": ETATS_DEFAUT["facture"], "unites": {}},
        },
        "plafond_journalier": plafond,
        "associer_regime_inconnu": str(associer) if associer not in (None, "non", "") else "",
        "regroupement_principal": options.get("regroupement_principal") or "aucun",
        "regroupement_age": options.get("regroupement_age") or "",
        "tranches_qf_perso": options.get("tranches_qf_perso") or "",
        "ventilation_periodes": "detaillees" if options.get("periodes_detaillees") else "simple",
        "regroupement_regime": bool(options.get("regroupement_regime")),
        "format_donnees": options.get("format_donnees") or "decimal",
        "filtres": [],
    }
