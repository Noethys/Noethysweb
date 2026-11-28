# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import ast, operator, re, json
from core.models import QuestionnaireQuestion

# Types de valeurs : texte, nombre, date, duree (en minutes), montant
# Totaux : "somme", "moyenne" ou None
# Mesure : la colonne se calcule à partir des consommations (période de calcul et unités paramétrables)

CATEGORIES = [
    ("individu", "Individu", [
        ("individu_nom_complet", "Nom complet", "Nom et prénom de l'individu", "texte", None),
        ("individu_nom", "Nom", "", "texte", None),
        ("individu_prenom", "Prénom", "", "texte", None),
        ("individu_sexe", "Genre", "M / F", "texte", None),
        ("individu_date_naiss", "Date de naissance", "", "date", None),
        ("individu_age", "Âge", "Âge à ce jour", "nombre", "moyenne"),
        ("individu_adresse_complete", "Adresse complète", "Rue, code postal et ville", "texte", None),
        ("individu_rue", "Rue", "", "texte", None),
        ("individu_cp", "Code postal", "", "texte", None),
        ("individu_ville", "Ville", "", "texte", None),
        ("individu_secteur", "Secteur", "Secteur géographique de l'individu", "texte", None),
        ("individu_tel_mobile", "Tél. portable", "Téléphone portable de l'individu", "texte", None),
        ("individu_age_debut", "Âge au début de la période", "Âge au premier jour de la période (utile pour les bilans CAF)", "nombre", "moyenne"),
        ("individu_tranche_age", "Tranche d'âge", "Selon l'âge au début de la période : moins de 3 ans, 3-5, 6-11, 12-17, 18 ans et plus", "texte", None),
    ]),
    ("contact", "Contact", [
        ("contact_tel_titulaires", "Téléphones des titulaires", "Portable et domicile des titulaires du dossier famille", "texte", None),
        ("contact_mail_titulaires", "E-mails des titulaires", "Adresses e-mail des titulaires du dossier famille", "texte", None),
    ]),
    ("famille", "Famille", [
        ("famille_nom_complet", "Famille", "Noms des titulaires de la famille", "texte", None),
        ("famille_num_allocataire", "N° allocataire", "Numéro d'allocataire de la famille", "texte", None),
        ("famille_allocataire", "Allocataire", "Nom de l'allocataire titulaire", "texte", None),
        ("famille_caisse", "Caisse", "Nom de la caisse de la famille", "texte", None),
        ("famille_qf", "Quotient familial", "QF valable à la fin de la période", "nombre", "moyenne"),
        ("famille_regime", "Régime social", "Régime de la caisse de la famille", "texte", None),
        ("famille_secteur", "Secteur (famille)", "Secteur géographique de la famille", "texte", None),
        ("famille_nbre_enfants", "Enfants présents de la famille", "Nombre d'individus de la même famille présents dans la liste", "nombre", None),
    ]),
    ("inscription", "Inscription", [
        ("inscription_groupe", "Groupe d'inscription", "Groupe(s) des inscriptions utilisées sur la période", "texte", None),
        ("inscription_categorie_tarif", "Catégorie de tarif", "Catégorie(s) de tarif des inscriptions utilisées", "texte", None),
        ("inscription_date", "Date d'inscription", "Date de début de l'inscription (la plus ancienne)", "date", None),
    ]),
    ("scolarite", "Scolarité", [
        ("individu_ecole", "École", "École fréquentée sur la période", "texte", None),
        ("individu_classe", "Classe", "Classe fréquentée sur la période", "texte", None),
        ("individu_niveau", "Niveau scolaire", "Niveau scolaire sur la période", "texte", None),
    ]),
    ("consommations", "Consommations", [
        ("*nbre_conso", "Nombre de consommations", "Nombre d'unités consommées sur la période", "nombre", "somme"),
        ("*jours_presence", "Jours de présence", "Dates distinctes avec au moins une réservation ou présence", "nombre", "somme"),
        ("*temps_conso", "Temps réel", "Somme des durées (heure de fin − heure de début)", "duree", "somme"),
        ("*temps_facture", "Temps facturé", "Temps facturé des prestations associées", "duree", "somme"),
        ("*equiv_journees", "Équivalence journées", "Selon le paramétrage des unités", "nombre", "somme"),
        ("*equiv_heures", "Équivalence heures", "Selon le paramétrage des unités", "duree", "somme"),
        ("*nbre_absences", "Nombre d'absences", "Absences justifiées et injustifiées, quels que soient les états cochés", "nombre", "somme"),
        ("*nbre_absentj", "Absences justifiées", "Quels que soient les états cochés", "nombre", "somme"),
        ("*nbre_absenti", "Absences injustifiées", "Quels que soient les états cochés", "nombre", "somme"),
        ("*reservations_non_pointees", "Réservations non pointées", "Réservations passées restées à l'état « réservation », quels que soient les états cochés", "nombre", "somme"),
        ("*jours_attente", "Jours en liste d'attente", "Dates distinctes en attente, quels que soient les états cochés", "nombre", "somme"),
        ("*premiere_date", "Première présence", "Première date avec une réservation ou une présence", "date", None),
        ("*derniere_date", "Dernière présence", "Dernière date avec une réservation ou une présence", "date", None),
        ("*heures_etat_global", "Heures (règles de l'état global)", "Heures calculées avec les règles par unité d'un profil de l'état global", "duree", "somme"),
        ("conso_activites", "Activité(s)", "Activités fréquentées sur la période", "texte", None),
        ("conso_groupes", "Groupe(s)", "Groupes fréquentés sur la période", "texte", None),
    ]),
    ("facturation", "Facturation", [
        ("*montant_facture", "Montant facturé", "Somme des prestations associées aux consommations", "montant", "somme"),
        ("*montant_regle", "Montant réglé", "Part déjà réglée de ces prestations", "montant", "somme"),
        ("*reste_du", "Reste dû", "Montant des prestations moins le montant réglé", "montant", "somme"),
        ("*montant_deductions", "Déductions", "Aides et déductions appliquées à ces prestations (CAF...)", "montant", "somme"),
    ]),
    ("sante", "Santé", [
        ("sante_regimes", "Régimes alimentaires", "Régimes alimentaires de l'individu", "texte", None),
        ("sante_informations", "Informations médicales", "Informations diffusables sur la liste des consommations, valables sur la période", "texte", None),
    ]),
    ("personnalisees", "Personnalisées", [
        ("calcul", "Colonne calculée", "Formule à partir des autres colonnes (ex : taux de présence)", "nombre", "somme"),
    ]),
]

# Colonnes calculées : formats et totaux possibles
FORMATS_CALCUL = {"nombre": "nombre", "duree": "duree", "montant": "montant", "pourcentage": "pourcentage"}
TOTAUX_CALCUL = {"somme": "somme", "moyenne": "moyenne", "aucun": None}

# Codes de mesures avec les suffixes de l'ancienne version
SUFFIXES_PERIODES = {"_hors_vacances": "hors_vacances", "_vacances": "vacances"} # L'ordre compte : "_hors_vacances" se termine aussi par "_vacances"
LABELS_PERIODES = {"vacances": "vacances", "hors_vacances": "hors vacances"}
CATEGORIES_RESTREINTES = {"sante": "informations_liste"} # Catégorie : permission nécessaire
TRANCHES_AGE = [(3, "Moins de 3 ans"), (6, "3 – 5 ans"), (12, "6 – 11 ans"), (18, "12 – 17 ans"), (None, "18 ans et plus")]

MODELES = [
    {"code": "liste_simple", "nom": "Liste nominative simple", "description": "Liste des individus présents sur la période", "colonnes": [
        ("individu_nom_complet", "Nom complet", {}),
        ("individu_date_naiss", "Date de naissance", {}),
        ("individu_age", "Âge", {}),
        ("individu_ville", "Ville", {}),
    ]},
    {"code": "caf", "nom": "Fréquentation CAF / bilan", "description": "Heures par enfant, vacances séparées", "colonnes": [
        ("individu_nom_complet", "Nom complet", {}),
        ("famille_num_allocataire", "N° allocataire", {}),
        ("famille_qf", "QF", {}),
        ("*equiv_heures", "Équiv. heures", {}),
        ("*equiv_heures", "Équiv. heures vacances", {"periode": "vacances"}),
    ]},
    {"code": "facturation", "nom": "Temps facturé par famille", "description": "Contrôle avant facturation", "colonnes": [
        ("famille_nom_complet", "Famille", {}),
        ("individu_nom_complet", "Nom complet", {}),
        ("*nbre_conso", "Nb conso", {}),
        ("*temps_facture", "Temps facturé", {}),
        ("*montant_facture", "Montant facturé", {}),
    ]},
    {"code": "assiduite", "nom": "Assiduité", "description": "Présences et absences par individu", "colonnes": [
        ("individu_nom_complet", "Nom complet", {}),
        ("*jours_presence", "Jours de présence", {}),
        ("*nbre_absentj", "Absences justifiées", {}),
        ("*nbre_absenti", "Absences injustifiées", {}),
    ]},
    {"code": "ecoles", "nom": "Effectifs par école", "description": "Répartition des individus par école et classe", "colonnes": [
        ("individu_nom_complet", "Nom complet", {}),
        ("individu_ecole", "École", {}),
        ("individu_classe", "Classe", {}),
        ("individu_niveau", "Niveau", {}),
        ("*nbre_conso", "Nb conso", {}),
    ]},
]


def Est_autorise(code_categorie="", utilisateur=None):
    permission = CATEGORIES_RESTREINTES.get(code_categorie)
    return not permission or (utilisateur is not None and utilisateur.has_perm("core.%s" % permission))


def Get_categories(utilisateur=None):
    """ Renvoie les catégories de colonnes, questionnaires inclus (les catégories restreintes nécessitent une permission) """
    categories = [(code, label, list(champs)) for code, label, champs in CATEGORIES if Est_autorise(code, utilisateur)]
    champs_questions = []
    for categorie, label_categorie in (("individu", "Individu"), ("famille", "Famille")):
        for question in QuestionnaireQuestion.objects.filter(categorie=categorie, visible=True).order_by("ordre"):
            champs_questions.append(("question_%d" % question.pk, question.label, "Questionnaire %s" % label_categorie.lower(), "texte", None))
    categories.append(("questionnaires", "Questionnaires", champs_questions))
    return categories


def Get_dict_champs(utilisateur=None):
    """ Renvoie un dict {code: infos du champ} """
    return {champ[0]: {"code": champ[0], "label": champ[1], "description": champ[2], "type": champ[3], "total": champ[4], "categorie": code_categorie}
            for code_categorie, label_categorie, champs in Get_categories(utilisateur) for champ in champs}


def Get_catalogue(utilisateur=None):
    """ Catalogue envoyé au sélecteur de colonnes """
    return [{"code": code, "label": label, "champs": [{"code": champ[0], "label": champ[1], "description": champ[2], "mesure": champ[0].startswith("*"), "calcul": champ[0] == "calcul"} for champ in champs]}
            for code, label, champs in Get_categories(utilisateur) if champs]


def Get_modeles():
    return [{"code": modele["code"], "nom": modele["nom"], "description": modele["description"],
             "colonnes": [dict({"code": code, "nom": nom, "periode": "toutes", "unites": []}, **options) for code, nom, options in modele["colonnes"]]}
            for modele in MODELES]


def Normaliser_colonne(colonne={}):
    """ Convertit une colonne (y compris de l'ancien format) au format actuel """
    code = colonne.get("code", "")
    periode = colonne.get("periode", "toutes") or "toutes"

    # Ancien format : la période était incluse dans le code (ex : *nbre_conso_vacances)
    if code.startswith("*"):
        for suffixe, valeur_periode in SUFFIXES_PERIODES.items():
            if code.endswith(suffixe):
                code = code[:-len(suffixe)]
                periode = valeur_periode
                break

    # Ancien format : les unités étaient saisies sous forme de texte séparé par des points-virgules
    unites = colonne.get("unites") or []
    if isinstance(unites, str):
        unites = [nom.strip() for nom in unites.split(";") if nom.strip()]

    resultat = {"nom": colonne.get("nom", ""), "code": code, "periode": periode if periode in ("toutes", "vacances", "hors_vacances") else "toutes",
                "unites": [nom for nom in unites if isinstance(nom, str)]}
    if code.startswith("*"):
        jours = colonne.get("jours") or []
        resultat["jours"] = sorted({int(jour) for jour in jours if str(jour).isdigit() and 0 <= int(jour) <= 6}) if isinstance(jours, list) else []
    if code == "*heures_etat_global":
        resultat["profil"] = int(colonne["profil"]) if str(colonne.get("profil") or "").isdigit() else None
    if code == "calcul":
        resultat["formule"] = str(colonne.get("formule") or "")[:LONGUEUR_MAX_FORMULE]
        resultat["format"] = colonne.get("format") if colonne.get("format") in FORMATS_CALCUL else "nombre"
        resultat["total"] = colonne.get("total") if colonne.get("total") in TOTAUX_CALCUL else "somme"
    return resultat


def Normaliser_colonnes(colonnes=[]):
    return [Normaliser_colonne(colonne) for colonne in colonnes if colonne.get("code") and colonne.get("code") != "aucun"]


# ---------------------------------------------------------------------------------------------------
# Colonnes calculées
# Syntaxe : [Titre d'une colonne], nombres (point décimal), textes entre guillemets, + - * / %,
# comparaisons (= == != < <= > >=), ET, OU, NON, SI(condition, alors, sinon), MIN(), MAX(), ARRONDI(valeur, décimales), ABS().
# Les durées valent des heures (7h30 = 7.5) et les cases vides valent 0 dans les opérations.
# L'évaluation se fait sur l'arbre syntaxique, avec une liste blanche, sans eval().
# ---------------------------------------------------------------------------------------------------

LONGUEUR_MAX_FORMULE = 500
REGEX_REFERENCE = re.compile(r"\[([^\[\]]+)\]")
REGEX_VARIABLE = re.compile(r"c\d+")

OPERATEURS_BINAIRES = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Mod: operator.mod}
OPERATEURS_COMPARAISON = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge}
FONCTIONS_CALCUL = {
    "MIN": lambda *args: min(args),
    "MAX": lambda *args: max(args),
    "ARRONDI": lambda valeur, decimales=0: round(valeur, int(decimales)),
    "ABS": lambda valeur: abs(valeur),
}


class Erreur_formule(Exception):
    pass


class Formule_colonne():
    def __init__(self, texte="", titres={}):
        """ titres : dict {titre en minuscules : index de la colonne} """
        self.texte = texte or ""
        if not self.texte.strip():
            raise Erreur_formule("la formule est vide")
        if len(self.texte) > LONGUEUR_MAX_FORMULE:
            raise Erreur_formule("la formule est trop longue")
        self.references = set()

        def Remplacer(correspondance):
            titre = correspondance.group(1).strip().lower()
            if titre not in titres:
                raise Erreur_formule("la colonne [%s] n'existe pas" % correspondance.group(1).strip())
            self.references.add(titres[titre])
            return " c%d " % titres[titre]

        source = REGEX_REFERENCE.sub(Remplacer, self.texte.replace("\n", " ").replace("\r", " "))
        source = re.sub(r"\bET\b", " and ", source)
        source = re.sub(r"\bOU\b", " or ", source)
        source = re.sub(r"\bNON\b", " not ", source)
        source = re.sub(r"(?<![=!<>])=(?!=)", "==", source)
        try:
            self.arbre = ast.parse(source.strip(), mode="eval")
        except SyntaxError:
            raise Erreur_formule("la formule contient une erreur de syntaxe")
        self.Verifier()

    def Verifier(self):
        autorises = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.USub, ast.UAdd, ast.Not, ast.BoolOp, ast.And, ast.Or, ast.Compare,
                     ast.Call, ast.Name, ast.Load, ast.Constant) + tuple(OPERATEURS_BINAIRES) + tuple(OPERATEURS_COMPARAISON)
        for element in ast.walk(self.arbre):
            if not isinstance(element, autorises):
                raise Erreur_formule("la formule contient un élément non autorisé")
            if isinstance(element, ast.Call):
                if not isinstance(element.func, ast.Name) or element.func.id not in list(FONCTIONS_CALCUL) + ["SI"] or element.keywords:
                    raise Erreur_formule("fonction inconnue (fonctions possibles : SI, MIN, MAX, ARRONDI, ABS)")
                if element.func.id == "SI" and len(element.args) not in (2, 3):
                    raise Erreur_formule("la fonction SI attend 2 ou 3 valeurs : SI(condition, alors, sinon)")
            elif isinstance(element, ast.Name) and not REGEX_VARIABLE.fullmatch(element.id) and element.id not in FONCTIONS_CALCUL and element.id != "SI":
                raise Erreur_formule("nom inconnu : %s (les colonnes s'écrivent entre crochets)" % element.id)
            if isinstance(element, ast.Constant) and (isinstance(element.value, bool) or not isinstance(element.value, (int, float, str))):
                raise Erreur_formule("la formule contient une valeur non autorisée")

    def Calculer(self, valeurs={}):
        """ valeurs : dict {index de colonne : valeur}. Renvoie None si le calcul est impossible (division par zéro...) """
        try:
            resultat = self._Evaluer(self.arbre.body, valeurs)
        except (ZeroDivisionError, TypeError, ValueError, OverflowError):
            return None
        if isinstance(resultat, bool):
            return 1 if resultat else 0
        return resultat

    def _Evaluer(self, noeud, valeurs):
        if isinstance(noeud, ast.Constant):
            return noeud.value
        if isinstance(noeud, ast.Name):
            return valeurs.get(int(noeud.id[1:]))
        if isinstance(noeud, ast.BinOp):
            gauche, droite = self._Evaluer(noeud.left, valeurs), self._Evaluer(noeud.right, valeurs)
            if (isinstance(gauche, str) or isinstance(droite, str)) and not (isinstance(noeud.op, ast.Add) and isinstance(gauche, str) and isinstance(droite, str)):
                raise TypeError("Seule l'addition de deux textes est possible")
            return OPERATEURS_BINAIRES[type(noeud.op)](0 if gauche is None else gauche, 0 if droite is None else droite)
        if isinstance(noeud, ast.UnaryOp):
            valeur = self._Evaluer(noeud.operand, valeurs)
            if isinstance(noeud.op, ast.Not):
                return not valeur
            valeur = 0 if valeur is None else valeur
            return -valeur if isinstance(noeud.op, ast.USub) else +valeur
        if isinstance(noeud, ast.BoolOp):
            if isinstance(noeud.op, ast.And):
                return all(self._Evaluer(element, valeurs) for element in noeud.values)
            return any(self._Evaluer(element, valeurs) for element in noeud.values)
        if isinstance(noeud, ast.Compare):
            gauche = self._Evaluer(noeud.left, valeurs)
            for operateur, comparateur in zip(noeud.ops, noeud.comparators):
                droite = self._Evaluer(comparateur, valeurs)
                if not OPERATEURS_COMPARAISON[type(operateur)](gauche, droite):
                    return False
                gauche = droite
            return True
        if isinstance(noeud, ast.Call):
            if noeud.func.id == "SI":
                # Seule la branche retenue est évaluée
                if self._Evaluer(noeud.args[0], valeurs):
                    return self._Evaluer(noeud.args[1], valeurs)
                return self._Evaluer(noeud.args[2], valeurs) if len(noeud.args) > 2 else 0
            arguments = [self._Evaluer(argument, valeurs) for argument in noeud.args]
            return FONCTIONS_CALCUL[noeud.func.id](*[0 if argument is None else argument for argument in arguments])
        raise Erreur_formule("élément non pris en charge")


def Get_tranche_age(age=None):
    if age is None:
        return None
    for limite, label in TRANCHES_AGE:
        if limite is None or age < limite:
            return label


def Preparer_regles_etat_global(parametre=None):
    """ Règles de calcul par unité d'un profil de l'état global, prêtes pour utils_frequentation_caf.Calcul.Calculer_valeur """
    from consommations.utils import utils_frequentation_caf
    donnees = utils_frequentation_caf.Convertir_profil_etat_global(json.loads(parametre.parametre))
    regles = {}
    for idunite, dict_unite in donnees["colonnes"]["realise"]["unites"].items():
        dict_unite = dict(dict_unite)
        if dict_unite["type"] == "0":
            dict_unite["coeff_delta"] = utils_frequentation_caf.Coeff_en_delta(dict_unite["coeff"])
        if dict_unite["type"] == "3":
            dict_unite["formule_compilee"] = utils_frequentation_caf.Formule(dict_unite["formule"])
        regles[int(idunite)] = dict_unite
    return {"unites": regles, "plafond_journalier": int(donnees.get("plafond_journalier") or 0)}
