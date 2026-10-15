# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

"""
Détection des doublons lors de la saisie d'un nouvel individu.

La comparaison tolère :
    - les accents, la casse, les tirets et les espaces (« Jean-Pierre » = « jean pierre ») ;
    - le nom de naissance (nom_jfille) ;
    - l'inversion du nom et du prénom ;
    - les fautes de frappe (distance de Damerau-Levenshtein et similarité de Jaro-Winkler) ;
    - les orthographes phonétiquement équivalentes, y compris sur la première lettre (« Kloé » / « Chloé », « Tomas » / « Thomas »).

Recherche des candidats en base (sans dépendre de la première lettre) :
    - même nom (ou nom de naissance) à l'accent et au tiret près, quel que soit le prénom ;
    - même prénom à l'accent et au tiret près, quel que soit le nom ;
    - mêmes initiales de nom et de prénom (fautes de frappe dans les deux champs) ;
    - nom et prénom inversés.

Niveaux renvoyés :
    3 = très probable : nom et prénom identiques une fois normalisés (ou inversés)
    2 = probable : l'un identique, l'autre très proche
    1 = à vérifier : nom et prénom proches
"""

import re
from functools import lru_cache
import jellyfish
from django.db.models import Q
from core.models import Individu, Rattachement
from core.utils import utils_texte

NIVEAUX = {3: "Très probable", 2: "Probable", 1: "À vérifier"}

# Variantes accentuées pour le préfiltrage en base sur la première lettre
VARIANTES = {"a": "aàâäáã", "e": "eéèêë", "i": "iîïí", "o": "oôöóõ", "u": "uùûüú", "c": "cç", "y": "yÿ", "n": "nñ"}


@lru_cache(maxsize=50000)
def Normaliser(texte):
    texte = utils_texte.Supprimer_accents(texte or "").lower()
    for caractere in "-'’_.,":
        texte = texte.replace(caractere, " ")
    return " ".join(texte.split())


@lru_cache(maxsize=50000)
def Compacter(texte):
    """ Version sans espace, pour comparer « Jean Pierre » et « Jeanpierre » """
    return Normaliser(texte).replace(" ", "")


# Règles phonétiques simplifiées pour le français (appliquées dans l'ordre sur le texte normalisé, sans espace)
REGLES_PHONETIQUES = [
    (r"(.)\1+", r"\1"),                       # lettres doublées
    (r"ph", "f"), (r"th", "t"), (r"sch|sh", "ch"),
    (r"^h", ""), (r"([^c])h", r"\1"),          # h muet (mais conserve ch)
    (r"c([eiy])", r"s\1"), (r"ch", "k"), (r"qu|ck|c|q", "k"), (r"x$", ""), (r"x", "ks"),
    (r"y", "i"), (r"w", "v"), (r"z(?!$)", "s"),
    (r"eau|au", "o"), (r"ai|ei", "e"), (r"ou", "u"), (r"([aeiou])s([aeiou])", r"\1z\2"),
    (r"(?<=.)e$", ""), (r"(?<=.)[tds]$", ""),   # lettres finales muettes (le z final, comme dans Martinez, est conservé)
    (r"(.)\1+", r"\1"),
]


REGLES_PHONETIQUES = [(re.compile(motif), remplacement) for motif, remplacement in REGLES_PHONETIQUES]


@lru_cache(maxsize=50000)
def Phonetique(texte):
    code = Compacter(texte)
    for motif, remplacement in REGLES_PHONETIQUES:
        code = motif.sub(remplacement, code)
    return code


@lru_cache(maxsize=100000)
def Est_proche(saisie, valeur):
    """ True si les deux textes normalisés sont très proches (faute de frappe, lettre manquante ou inversée) """
    a, b = Compacter(saisie), Compacter(valeur)
    if not a or not b:
        return False
    if a == b:
        return True
    # Orthographe phonétiquement équivalente, y compris sur la première lettre (Kloé / Chloé, Tomas / Thomas)
    if min(len(a), len(b)) >= 3 and len(Phonetique(a)) >= 2 and Phonetique(a) == Phonetique(b):
        return True
    distance = jellyfish.damerau_levenshtein_distance(a, b)
    if min(len(a), len(b)) <= 3:
        # Mots très courts : seule une lettre oubliée ou en trop est tolérée (Ema / Emma), pas une lettre différente (Léo / Léa)
        return distance == 1 and len(a) != len(b)
    # Une faute pour un mot court, deux au-delà de 7 lettres (MARTIN et MARTINEZ ne sont pas rapprochés)
    if distance <= (1 if min(len(a), len(b)) <= 7 else 2):
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    similarite = jellyfish.jaro_winkler_similarity(a, b)
    # Lettre déplacée ou orthographe phonétiquement équivalente (Chloé / Clohé)
    return similarite >= 0.93 or (similarite >= 0.85 and jellyfish.soundex(a) == jellyfish.soundex(b))


def Est_identique(saisie, valeur):
    return bool(Compacter(saisie)) and Compacter(saisie) == Compacter(valeur)


def Prenom_compatible(saisie, valeur):
    """ Prénom identique ou prénom composé dont la première partie correspond (« Jean » / « Jean-Pierre ») """
    a, b = Normaliser(saisie), Normaliser(valeur)
    if not a or not b:
        return False
    return a.split()[0] == b.split()[0] and (len(a.split()) > 1 or len(b.split()) > 1)


def Get_motif_equivalent(texte):
    """ Expression régulière qui reconnaît le texte à la casse, aux accents, aux tirets et aux espaces près (« Jean-Pierre » = « jean pierre » = « Jeanpierre ») """
    mots = Normaliser(texte).split()
    if not mots:
        return None
    morceaux = []
    for mot in mots:
        morceaux.append("".join("[%s]" % VARIANTES[lettre] if lettre in VARIANTES else re.escape(lettre) for lettre in mot))
    return "^ *%s *$" % "[- '’]*".join(morceaux)


def Get_conditions_equivalent(champ, texte):
    """ Q() : le champ est égal au texte à la casse, aux accents, aux tirets et aux espaces près """
    motif = Get_motif_equivalent(texte)
    return Q(**{"%s__iregex" % champ: motif}) if motif else Q(pk__in=[])


def Get_conditions_initiale(champ, texte):
    """ Q() : le champ commence par la même lettre que le texte (avec ses variantes accentuées et en majuscules) """
    initiale = Normaliser(texte)[:1]
    if not initiale:
        return Q(pk__in=[])
    conditions = Q()
    for variante in VARIANTES.get(initiale, initiale):
        conditions |= Q(**{"%s__istartswith" % champ: variante}) | Q(**{"%s__istartswith" % champ: variante.upper()})
    return conditions


def Evaluer(nom, prenom, candidat, sans_prenom=False):
    """ Renvoie (niveau, motif) ou (0, None) """
    noms_candidat = [n for n in (candidat["nom"], candidat["nom_jfille"]) if n]
    nom_identique = any(Est_identique(nom, n) for n in noms_candidat)
    nom_proche = nom_identique or any(Est_proche(nom, n) for n in noms_candidat)
    via_nom_naissance = not Est_identique(nom, candidat["nom"]) and candidat["nom_jfille"] and Est_identique(nom, candidat["nom_jfille"])

    # Organismes et fiches sans prénom : comparaison sur le nom seul
    if sans_prenom:
        if nom_identique:
            return 3, "Même nom"
        if nom_proche:
            return 2, "Nom très proche"
        return 0, None

    prenom_identique = Est_identique(prenom, candidat["prenom"])
    prenom_proche = prenom_identique or Est_proche(prenom, candidat["prenom"]) or Prenom_compatible(prenom, candidat["prenom"])

    if nom_identique and prenom_identique:
        return 3, "Nom de naissance identique" if via_nom_naissance else "Même nom et même prénom"
    if Est_identique(nom, candidat["prenom"]) and Est_identique(prenom, candidat["nom"]):
        return 3, "Nom et prénom inversés"
    if (nom_identique and prenom_proche) or (nom_proche and prenom_identique):
        return 2, "Orthographe très proche"
    if nom_proche and prenom_proche:
        return 1, "Orthographe proche"
    return 0, None


def Rechercher_doublons(nom="", prenom="", sans_prenom=False, idfamille=None, limite=8):
    """ Renvoie la liste des individus existants pouvant être des doublons, du plus probable au moins probable """
    nom, prenom = (nom or "").strip(), (prenom or "").strip()
    if len(Compacter(nom)) < 2 or (not sans_prenom and len(Compacter(prenom)) < 2):
        return []

    # Préfiltrage en base (voir l'en-tête du module) : la première lettre peut différer dès que l'un des deux champs correspond
    nom_equivalent = Get_conditions_equivalent("nom", nom) | Get_conditions_equivalent("nom_jfille", nom)
    initiales_nom = Get_conditions_initiale("nom", nom) | Get_conditions_initiale("nom_jfille", nom)
    if sans_prenom:
        conditions = nom_equivalent | initiales_nom
    else:
        conditions = nom_equivalent | Get_conditions_equivalent("prenom", prenom) | (initiales_nom & Get_conditions_initiale("prenom", prenom)) \
                     | (Get_conditions_equivalent("prenom", nom) & Get_conditions_equivalent("nom", prenom)) \
                     | (Get_conditions_initiale("prenom", nom) & Get_conditions_initiale("nom", prenom))
    candidats = Individu.objects.filter(conditions).values("pk", "nom", "prenom", "nom_jfille")

    resultats = []
    for candidat in candidats.iterator():
        niveau, motif = Evaluer(nom, prenom, candidat, sans_prenom=sans_prenom)
        if niveau:
            resultats.append({"idindividu": candidat["pk"], "niveau": niveau, "motif": motif})
    resultats.sort(key=lambda resultat: (-resultat["niveau"], resultat["idindividu"]))
    resultats = resultats[:limite]
    if not resultats:
        return []

    # Informations complémentaires : date de naissance (champ chiffré) et familles
    individus = Individu.objects.in_bulk([resultat["idindividu"] for resultat in resultats])
    familles = {}
    for rattachement in Rattachement.objects.select_related("famille").filter(individu_id__in=individus.keys(), famille__isnull=False):
        familles.setdefault(rattachement.individu_id, []).append(rattachement.famille)
    for resultat in resultats:
        individu = individus[resultat["idindividu"]]
        resultat.update({
            "individu": individu,
            "label_niveau": NIVEAUX[resultat["niveau"]],
            "age": individu.Get_age(),
            "familles": familles.get(individu.pk, []),
            "deja_membre": bool(idfamille) and any(famille.pk == int(idfamille) for famille in familles.get(individu.pk, [])),
        })
    return resultats
