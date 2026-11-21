# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

"""
Délais de conservation mémorisés du nettoyeur.
Ils sont communs à toute l'instance (paramètre sans utilisateur) car ils traduisent la politique de conservation
définie par le référent RGPD de l'organisateur. Ils sont aussi utilisés par l'encart de la page d'accueil.
Format : {"code_operation": {"mois": 24}} ou {"code_operation": {"date": "2023-01-31"}}
"""

import datetime, json, logging
logger = logging.getLogger(__name__)
from outils.utils.nettoyeur.base import CHOIX_DELAIS, Get_date_limite

CATEGORIE = "nettoyeur"
NOM = "delais"
MOIS_AUTORISES = [mois for mois, label in CHOIX_DELAIS]


def Get_delais():
    """ Renvoie les délais mémorisés (dict). Lecture seule : aucun paramètre n'est créé s'il n'existe pas. """
    from core.models import Parametre
    try:
        parametre = Parametre.objects.filter(nom=NOM, categorie=CATEGORIE, utilisateur__isnull=True).order_by("-pk").first()
        delais = json.loads(parametre.parametre) if parametre and parametre.parametre else {}
    except Exception:
        logger.exception("Nettoyeur : lecture des délais mémorisés impossible")
        return {}
    return delais if isinstance(delais, dict) else {}


def Set_delais(delais={}):
    from core.utils import utils_parametres
    utils_parametres.Set(nom=NOM, categorie=CATEGORIE, utilisateur=None, valeur=delais or {})


def Valider_delai(operation=None, delai=None):
    """ Renvoie le délai nettoyé ({"mois": N} ou {"date": "AAAA-MM-JJ"}) ou None s'il n'est pas valide """
    if operation is None or operation.delai_defaut is None or not isinstance(delai, dict):
        return None
    if "mois" in delai:
        try:
            mois = int(delai["mois"])
        except (TypeError, ValueError):
            return None
        if mois in MOIS_AUTORISES and not operation.Check_date_limite(Get_date_limite(mois)):
            return {"mois": mois}
        return None
    if "date" in delai:
        try:
            date = datetime.datetime.strptime(str(delai["date"]), "%Y-%m-%d").date()
        except ValueError:
            return None
        if not operation.Check_date_limite(date):
            return {"date": date.strftime("%Y-%m-%d")}
    return None


def Get_delai_operation(operation=None, delais=None):
    """ Renvoie le délai mémorisé et valide d'une opération ou son délai par défaut """
    if delais is None:
        delais = Get_delais()
    delai = Valider_delai(operation, delais.get(operation.code))
    if delai:
        return delai
    return {"mois": operation.delai_defaut} if operation.delai_defaut else None


def Get_date_limite_operation(operation=None, delais=None):
    """ Renvoie la date limite correspondant au délai mémorisé de l'opération (ou None si l'opération n'utilise pas de date) """
    delai = Get_delai_operation(operation, delais)
    if not delai:
        return None
    if "date" in delai:
        return datetime.datetime.strptime(delai["date"], "%Y-%m-%d").date()
    return Get_date_limite(delai["mois"])
