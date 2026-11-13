# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

"""
Traduction des erreurs de validation XSD (lxml) en messages compréhensibles par les utilisateurs.

Pour chaque erreur, on identifie :
- QUI est concerné (débiteur / pièce / lot / en-tête du fichier), en remontant dans le XML depuis l'élément fautif,
- QUOI : le champ concerné, traduit en français, et l'écran où le corriger,
- le PROBLEME : caractères interdits, valeur trop longue, champ vide, format incorrect...
Le message technique d'origine reste disponible dans un bloc repliable pour le support.
"""

import logging, re
from html import escape
logger = logging.getLogger(__name__)

NBRE_MAX_ERREURS = 30


# ---------------------------------------------------------------------------------------------------------------------
#  Libellés des champs : nom de balise => (libellé, où corriger)
# ---------------------------------------------------------------------------------------------------------------------

AIDE_LOT_SEPA = "les paramètres du lot (bouton Modifier les paramètres)"
AIDE_MANDAT = "la fiche famille > Mandats"
AIDE_CREANCIER = "Paramétrage > Comptes bancaires (secteur public : Paramétrage > Perceptions)"

CHAMPS_SEPA = {
    "MsgId": ("l'identifiant du fichier", "le nom du lot (bouton Modifier les paramètres)"),
    "CreDtTm": ("la date de création du fichier", None),
    "NbOfTxs": ("le nombre de prélèvements", None),
    "CtrlSum": ("le montant total", None),
    "PmtInfId": ("l'identifiant du lot", "le nom du lot (bouton Modifier les paramètres)"),
    "ReqdColltnDt": ("la date de prélèvement", AIDE_LOT_SEPA),
    "SeqTp": ("la séquence du prélèvement (FRST, RCUR...)", "la pièce du lot ou %s" % AIDE_MANDAT),
    "EndToEndId": ("la référence de la transaction", None),
    "InstdAmt": ("le montant du prélèvement", "la pièce du lot"),
    "MndtId": ("la référence unique du mandat (RUM)", AIDE_MANDAT),
    "DtOfSgntr": ("la date de signature du mandat", AIDE_MANDAT),
    "Ustrd": ("le libellé du prélèvement", "le motif du lot ou le libellé de la pièce"),
}

CHAMPS_ADRESSE_SEPA = {
    "StrtNm": "la rue", "BldgNb": "le numéro de voie", "BldgNm": "le bâtiment ou la résidence", "Flr": "l'étage",
    "PstBx": "la boîte postale", "PstCd": "le code postal", "TwnNm": "la ville", "Ctry": "le code pays",
    "Dept": "le service", "AdrLine": "la ligne d'adresse",
}

AIDE_EXPORT = "les paramètres de l'export (bouton Modifier les paramètres)"
AIDE_MODELE = "Paramétrage > Modèles d'exports vers le Trésor public"
AIDE_TITULAIRE = "la fiche de l'individu titulaire Hélios (fiche famille)"
AIDE_FAMILLE = "la fiche famille (paramètres Hélios)"
AIDE_PES_MANDAT = "la fiche famille > Mandats"

CHAMPS_PES = {
    # En-tête et bordereau
    "IdPost": ("le poste comptable", AIDE_MODELE),
    "IdColl": ("l'identifiant de la collectivité (SIRET)", AIDE_MODELE),
    "CodCol": ("le code collectivité", AIDE_MODELE),
    "CodBud": ("le code budget", AIDE_MODELE),
    "Exer": ("l'exercice", AIDE_EXPORT),
    "IdBord": ("l'identifiant du bordereau", AIDE_EXPORT),
    "DteBordEm": ("la date d'émission", AIDE_EXPORT),
    "DteStr": ("la date de création du fichier", None),
    "NomFic": ("le nom du fichier", AIDE_EXPORT),
    "NbrPce": ("le nombre de pièces", None),
    "MtBordHt": ("le montant total du bordereau", None),
    "TypBord": ("le type de bordereau", AIDE_MODELE),
    "TypFic": ("le type de fichier", None),
    # Pièce
    "IdPce": ("le numéro de la pièce", None),
    "TypPce": ("le type de pièce", AIDE_MODELE),
    "NatPce": ("la nature de la pièce", AIDE_MODELE),
    "ObjPce": ("l'objet de la pièce", "le libellé de la pièce dans %s" % AIDE_MODELE),
    "NumDette": ("le numéro de dette (numéro de facture)", "la facture"),
    "NumeroFacture": ("le numéro de facture", "la facture"),
    "Edition": ("le mode d'édition de l'ASAP", AIDE_MODELE),
    "DteAsp": ("la date de l'ASAP", AIDE_EXPORT),
    "CodRes": ("le code de résidence", AIDE_MODELE),
    # Ligne de pièce
    "IdLigne": ("le numéro de ligne", None),
    "ObjLignePce": ("le libellé de la ligne de pièce", "le libellé de la pièce dans %s" % AIDE_MODELE),
    "CodProdLoc": ("le code produit local", "l'activité ou %s" % AIDE_MODELE),
    "Nature": ("la nature comptable", "l'activité ou %s" % AIDE_MODELE),
    "Majo": ("le code de majoration", None),
    "MtHT": ("le montant", "la facture"),
    # Tiers
    "CatTiers": ("la catégorie de tiers", AIDE_FAMILLE),
    "NatJur": ("la nature juridique du tiers", AIDE_FAMILLE),
    "TypTiers": ("le type de tiers", AIDE_FAMILLE),
    "IdTiers": ("l'identifiant du tiers", AIDE_FAMILLE),
    "NatIdTiers": ("la nature de l'identifiant du tiers", AIDE_FAMILLE),
    "RefTiers": ("la référence du tiers", AIDE_FAMILLE),
    "Civilite": ("la civilité du titulaire Hélios", AIDE_TITULAIRE),
    "Nom": ("le nom du titulaire Hélios", AIDE_TITULAIRE),
    "Prenom": ("le prénom du titulaire Hélios", AIDE_TITULAIRE),
    "Sigle": ("le sigle du tiers", AIDE_FAMILLE),
    "TvaIntraCom": ("le numéro de TVA intracommunautaire", AIDE_FAMILLE),
    "TypAdr": ("le type d'adresse", None),
    "Adr2": ("la rue du titulaire Hélios", AIDE_TITULAIRE),
    "CP": ("le code postal du titulaire Hélios", AIDE_TITULAIRE),
    "Ville": ("la ville du titulaire Hélios", AIDE_TITULAIRE),
    # Prélèvement
    "IBAN": ("l'IBAN du mandat", AIDE_PES_MANDAT),
    "BIC": ("le BIC du mandat", AIDE_PES_MANDAT),
    "TitCpte": ("le titulaire du compte", AIDE_PES_MANDAT),
    "RefUniMdt": ("la référence unique du mandat (RUM)", AIDE_PES_MANDAT),
    "DateSignMandat": ("la date de signature du mandat", AIDE_PES_MANDAT),
    "DtePrel": ("la date de prélèvement", AIDE_EXPORT),
    "MtPrel": ("le montant prélevé", "la pièce de l'export"),
    "SequencePres": ("la séquence du prélèvement", "la pièce de l'export"),
    "LibPrel": ("le libellé du prélèvement", "le libellé du prélèvement dans %s" % AIDE_MODELE),
    "NatPrel": ("la nature du prélèvement", None),
    "PerPrel": ("la périodicité du prélèvement", None),
    # Pièces jointes
    "NomPJ": ("le nom de la facture PDF jointe", None),
    "IdUnique": ("l'identifiant de la facture PDF jointe", None),
    "TypePJ": ("le type de pièce jointe", AIDE_MODELE),
    "Description": ("la description de la pièce jointe", None),
}


def Get_champ_sepa(nom="", ancetres=[]):
    """ Renvoie (libellé, aide) pour un élément d'un fichier SEPA pain.008 """
    if nom in CHAMPS_SEPA:
        return CHAMPS_SEPA[nom]

    cote_debiteur = any(a in ("Dbtr", "DbtrAcct", "DbtrAgt", "UltmtDbtr") for a in ancetres)
    qui = "du titulaire du compte débité" if cote_debiteur else "du créancier"
    aide = AIDE_MANDAT if cote_debiteur else AIDE_CREANCIER

    if nom in CHAMPS_ADRESSE_SEPA:
        return ("%s %s" % (CHAMPS_ADRESSE_SEPA[nom], qui), aide)
    if nom == "Nm":
        if "InitgPty" in ancetres:
            return ("la raison sociale du créancier", "Paramétrage > Comptes bancaires")
        return ("le nom %s" % qui, aide)
    if nom == "IBAN":
        return ("l'IBAN %s" % qui, aide)
    if nom in ("BIC", "BICFI"):
        return ("le BIC %s" % qui, aide)
    if nom == "Id":
        if "CdtrSchmeId" in ancetres:
            return ("l'identifiant créancier SEPA (ICS)", "Paramétrage > Comptes bancaires")
        if "InitgPty" in ancetres:
            return ("le SIRET de l'organisateur", "Paramétrage > Organisateur")
    return ("l'information '%s'" % nom, None)


def Get_champ_pes(nom="", ancetres=[]):
    """ Renvoie (libellé, aide) pour un élément d'un fichier PES V2 """
    return CHAMPS_PES.get(nom, ("l'information '%s'" % nom, None))


# ---------------------------------------------------------------------------------------------------------------------
#  Identification de la personne / de la pièce concernée
# ---------------------------------------------------------------------------------------------------------------------

def Nom_local(element):
    try:
        return element.tag.split("}")[-1]
    except Exception:
        return ""


def Texte(element, chemin):
    """ Texte ou attribut V d'un sous-élément (namespace ignoré) """
    trouve = element.find(chemin)
    if trouve is None:
        return ""
    return (trouve.get("V") or trouve.text or "").strip()


def Get_contexte_sepa(element):
    for ancetre in [element] + list(element.iterancestors()):
        nom = Nom_local(ancetre)
        if nom == "DrctDbtTxInf":
            debiteur = Texte(ancetre, ".//{*}Dbtr/{*}Nm")
            rum = Texte(ancetre, ".//{*}MndtId")
            texte = debiteur or "Prélèvement sans nom de débiteur"
            return "%s (mandat %s)" % (texte, rum) if rum else texte
        if nom == "PmtInf":
            sequence = Texte(ancetre, ".//{*}SeqTp")
            return "Lot de prélèvements%s" % (" (séquence %s)" % sequence if sequence else "")
    return "Paramètres généraux du fichier"


def Get_contexte_pes(element):
    for ancetre in [element] + list(element.iterancestors()):
        nom = Nom_local(ancetre)
        if nom == "PJ":
            return "Facture PDF jointe %s" % Texte(ancetre, ".//{*}NomPJ")
        if nom == "Piece":
            id_piece = Texte(ancetre, ".//{*}IdPce")
            debiteur = " ".join([texte for texte in (Texte(ancetre, ".//{*}Tiers//{*}Nom"), Texte(ancetre, ".//{*}Tiers//{*}Prenom")) if texte])
            texte = "Pièce n°%s" % id_piece if id_piece else "Pièce"
            return "%s (%s)" % (texte, debiteur) if debiteur else texte
        if nom == "Bordereau":
            return "Bordereau"
    return "En-tête du fichier"


# ---------------------------------------------------------------------------------------------------------------------
#  Traduction du problème
# ---------------------------------------------------------------------------------------------------------------------

def Formate_valeur(valeur=""):
    if len(valeur) > 60:
        valeur = valeur[:57] + "..."
    return "« %s »" % escape(valeur)


def Get_noms_attendus(message=""):
    """ Extrait les balises attendues d'un message 'Expected is ( ... )' """
    resultat = re.search(r"Expected is (?:one of )?\(\s*(.*?)\s*\)", message)
    if not resultat:
        return []
    return [nom.split("}")[-1].strip() for nom in resultat.group(1).split(",") if nom.strip()]


def Get_probleme(erreur, message="", fonction_champ=None, ancetres=[]):
    """ Renvoie une phrase décrivant le problème, à placer après le libellé du champ """
    type_erreur = erreur.type_name or ""
    valeur = re.search(r"The value '(.*?)'(?: is| has)", message) or re.search(r"Element '[^']*'(?:, attribute '[^']*')?: '(.*?)' is not a valid value", message)
    valeur = valeur.group(1) if valeur else None

    if "PATTERN" in type_erreur:
        if valeur is not None and valeur.strip() == "":
            return "information obligatoire non renseignée"
        if valeur and any(ord(caractere) > 127 for caractere in valeur):
            return "accents ou caractères spéciaux non autorisés dans %s" % Formate_valeur(valeur)
        return "caractères non autorisés ou format incorrect : %s" % Formate_valeur(valeur or "")

    if "MAXLENGTH" in type_erreur:
        longueurs = re.search(r"length of '(\d+)'; this exceeds the allowed maximum length of '(\d+)'", message)
        if longueurs:
            return "texte trop long (%s caractères pour %s maximum)%s" % (longueurs.group(1), longueurs.group(2), " : %s" % Formate_valeur(valeur) if valeur else "")
        return "texte trop long"

    if "MINLENGTH" in type_erreur:
        if re.search(r"length of '0'", message):
            return "information obligatoire non renseignée"
        minimum = re.search(r"minimum length of '(\d+)'", message)
        return "texte trop court%s" % (" (%s caractères minimum)" % minimum.group(1) if minimum else "")

    if "ENUMERATION" in type_erreur:
        return "valeur non autorisée%s" % (" : %s" % Formate_valeur(valeur) if valeur else "")

    if "TOTALDIGITS" in type_erreur or "FRACTIONDIGITS" in type_erreur:
        return "nombre comportant trop de chiffres%s" % (" : %s" % Formate_valeur(valeur) if valeur else "")

    if "MININCLUSIVE" in type_erreur or "MINEXCLUSIVE" in type_erreur:
        return "valeur trop petite (montant nul ou négatif ?)%s" % (" : %s" % Formate_valeur(valeur) if valeur else "")

    if "MAXINCLUSIVE" in type_erreur or "MAXEXCLUSIVE" in type_erreur:
        return "valeur trop grande%s" % (" : %s" % Formate_valeur(valeur) if valeur else "")

    if "DATATYPE" in type_erreur:
        type_attendu = re.search(r"atomic type '(?:xs:)?(\w+)'", message)
        formats = {"date": "une date", "dateTime": "une date et une heure", "decimal": "un nombre", "integer": "un nombre entier", "boolean": "oui/non"}
        attendu = formats.get(type_attendu.group(1)) if type_attendu else None
        if valeur is not None and valeur.strip() == "":
            return "information obligatoire non renseignée"
        return "format incorrect%s%s" % (" : %s" % Formate_valeur(valeur) if valeur is not None else "", " (attendu : %s)" % attendu if attendu else "")

    if "Missing child element" in message:
        libelles = [fonction_champ(nom, ancetres)[0] for nom in Get_noms_attendus(message)]
        if libelles:
            return "MANQUANT:%s" % " ou ".join(libelles)
        return "MANQUANT:"

    if "is required but missing" in message:
        return "information obligatoire non renseignée"

    if "This element is not expected" in message:
        return "INATTENDU"

    return "valeur non conforme à la norme"


# ---------------------------------------------------------------------------------------------------------------------
#  Fonction principale
# ---------------------------------------------------------------------------------------------------------------------

def Traduire_erreurs(error_log=None, doc=None, format="sepa"):
    """ Renvoie une liste de messages HTML compréhensibles à partir du error_log lxml """
    fonction_champ = Get_champ_pes if format == "pes" else Get_champ_sepa
    fonction_contexte = Get_contexte_pes if format == "pes" else Get_contexte_sepa

    messages, deja_vus = [], set()
    erreurs = list(error_log or [])
    for erreur in erreurs:
        message_technique = "Ligne %d : %s" % (erreur.line, erreur.message)
        try:
            message = erreur.message or ""

            # Recherche de l'élément concerné
            element = None
            if doc is not None and erreur.path:
                resultats = doc.xpath(erreur.path)
                element = resultats[0] if resultats else None
            if element is None:
                raise ValueError("Elément introuvable")

            nom = Nom_local(element)
            ancetres = [Nom_local(ancetre) for ancetre in element.iterancestors()]
            contexte = fonction_contexte(element)
            libelle, aide = fonction_champ(nom, ancetres)
            probleme = Get_probleme(erreur, message, fonction_champ, [nom] + ancetres)

            # Toutes les balises du fichier étant générées par Noethysweb, une balise signalée comme "inattendue" alors que
            # libxml indique la liste des balises attendues révèle une information obligatoire omise car vide
            noms_attendus = Get_noms_attendus(message)
            if probleme == "INATTENDU" and noms_attendus:
                libelles = [fonction_champ(nom_attendu, ancetres)[0] for nom_attendu in noms_attendus]
                libelles_connus = [texte for texte in libelles if not texte.startswith("l'information '")]
                probleme = "MANQUANT:%s" % (" ou ".join(libelles_connus) if libelles_connus else "balise %s" % ", ".join(noms_attendus[:3]))
                ancetres_manquant = ancetres
            else:
                ancetres_manquant = [nom] + ancetres

            # Construction de la phrase
            if probleme.startswith("MANQUANT:"):
                manquant = probleme.split(":", 1)[1]
                phrase = "information obligatoire manquante : %s" % manquant if manquant else "information obligatoire manquante dans %s" % libelle
                if manquant:
                    aides = [fonction_champ(nom_attendu, ancetres_manquant)[1] for nom_attendu in noms_attendus]
                    aide = next((texte for texte in aides if texte), None)
            elif probleme == "INATTENDU":
                phrase = "information inattendue à cet endroit du fichier (%s). Il s'agit probablement d'une anomalie de Noethysweb : transmettez ce message au support" % libelle
                aide = None
            else:
                phrase = "%s : %s" % (libelle, probleme)
            phrase = phrase[0].upper() + phrase[1:]

            texte = "<b>%s</b> : %s." % (escape(contexte), phrase)
            if aide:
                texte += " <i>A corriger dans %s.</i>" % escape(aide)

        except Exception as err:
            logger.debug("Traduction impossible de l'erreur XSD : %s" % err)
            texte = "Le fichier n'est pas conforme à la norme."

        # Evite les doublons (même message pour plusieurs lignes identiques)
        if texte in deja_vus:
            continue
        deja_vus.add(texte)

        texte += " <details class='d-inline'><summary class='text-muted small' style='display:inline;cursor:pointer;'>Détail technique</summary><span class='text-muted small'>%s</span></details>" % escape(message_technique)
        messages.append(texte)

    if len(messages) > NBRE_MAX_ERREURS:
        reste = len(messages) - NBRE_MAX_ERREURS
        messages = messages[:NBRE_MAX_ERREURS] + ["... et %d autre%s erreur%s." % (reste, "s" if reste > 1 else "", "s" if reste > 1 else "")]

    return messages
