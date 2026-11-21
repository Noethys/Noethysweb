# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Encart de la page d'accueil signalant qu'un nettoyage est recommandé (superutilisateurs uniquement).
    Le résultat du calcul est enregistré dans la base (table des paramètres) et non dans le cache de Django : le cache
    par défaut est propre à chaque processus du serveur web, ce qui multiplierait les calculs et empêcherait la mise
    à jour de l'encart sur tous les processus après un nettoyage. """

import datetime, json, logging
logger = logging.getLogger(__name__)
from django.conf import settings
from outils.utils.nettoyeur.base import Formate_taille, Formate_nombre

DUREE_MASQUAGE_MOIS = 1
CATEGORIE_PARAMETRES = "nettoyeur"
NOM_PARAMETRE_ALERTE = "alerte_accueil"
FORMAT_HORODATAGE = "%Y-%m-%d %H:%M:%S"


def Reinitialiser():
    """ Efface le résultat enregistré : il sera recalculé au prochain affichage de la page d'accueil """
    from core.models import Parametre
    Parametre.objects.filter(categorie=CATEGORIE_PARAMETRES, nom=NOM_PARAMETRE_ALERTE, utilisateur__isnull=True).delete()


def Enregistrer(alerte=None):
    from core.models import Parametre
    valeur = dict(alerte)
    valeur["date_calcul"] = alerte["date_calcul"].strftime(FORMAT_HORODATAGE)
    valeur["dernier_nettoyage"] = alerte["dernier_nettoyage"].strftime(FORMAT_HORODATAGE) if alerte["dernier_nettoyage"] else None
    Parametre.objects.filter(categorie=CATEGORIE_PARAMETRES, nom=NOM_PARAMETRE_ALERTE, utilisateur__isnull=True).delete()
    Parametre.objects.create(categorie=CATEGORIE_PARAMETRES, nom=NOM_PARAMETRE_ALERTE, utilisateur=None, parametre=json.dumps(valeur))


def Lire():
    """ Renvoie le résultat enregistré ou None """
    from core.models import Parametre
    parametre = Parametre.objects.filter(categorie=CATEGORIE_PARAMETRES, nom=NOM_PARAMETRE_ALERTE, utilisateur__isnull=True).order_by("-pk").first()
    if not parametre or not parametre.parametre:
        return None
    try:
        alerte = json.loads(parametre.parametre)
        alerte["date_calcul"] = datetime.datetime.strptime(alerte["date_calcul"], FORMAT_HORODATAGE)
        if alerte.get("dernier_nettoyage"):
            alerte["dernier_nettoyage"] = datetime.datetime.strptime(alerte["dernier_nettoyage"], FORMAT_HORODATAGE)
        return alerte
    except (ValueError, KeyError, TypeError):
        return None


def Calculer():
    """ Analyse les opérations signalées sur la page d'accueil avec les délais mémorisés (ou par défaut) """
    from outils.utils.nettoyeur import Get_operations
    from core.models import Nettoyage
    from outils.utils.nettoyeur import utils_delais
    items = []
    cache_operations = {}
    delais = utils_delais.Get_delais()
    for operation in Get_operations(cache=cache_operations):
        if not operation.alerte_accueil:
            continue
        try:
            date_limite = utils_delais.Get_date_limite_operation(operation, delais)
            resultat = operation.Analyser(date_limite=date_limite)
        except Exception:
            logger.exception("Nettoyeur : erreur lors de l'analyse de l'opération %s pour l'accueil" % operation.code)
            continue
        if operation.Is_suggestion(resultat):
            valeur = Formate_nombre(resultat.nbre)
            if resultat.octets:
                valeur += " · %s" % Formate_taille(resultat.octets)
            items.append({"code": operation.code, "categorie": operation.categorie, "icone": operation.icone,
                          "label": operation.label_alerte or operation.titre, "valeur": valeur, "nbre_texte": Formate_nombre(resultat.nbre),
                          "octets_texte": Formate_taille(resultat.octets) if resultat.octets else "", "titre": operation.titre, "nbre": resultat.nbre, "octets": resultat.octets})

    dernier = Nettoyage.objects.order_by("-horodatage").first()
    return {
        "date_calcul": datetime.datetime.now(),
        "items": items,
        "octets": sum([item["octets"] for item in items]),
        "dernier_nettoyage": dernier.horodatage if dernier else None,
    }


def Get_alerte(request=None, forcer=False):
    """ Renvoie le contenu de l'encart ou None s'il ne doit pas être affiché """
    if not request or not request.user.is_superuser or settings.MODE_DEMO:
        return None

    # Masquage demandé par l'utilisateur
    from core.utils import utils_parametres
    masquer_jusqu = utils_parametres.Get(nom="masquer_alerte_jusqu", categorie=CATEGORIE_PARAMETRES, utilisateur=request.user, valeur="")
    if masquer_jusqu and not forcer:
        try:
            if datetime.datetime.strptime(masquer_jusqu, "%Y-%m-%d").date() >= datetime.date.today():
                return None
        except ValueError:
            pass

    # Calcul une fois par jour pour toute l'instance
    alerte = Lire()
    if not alerte or alerte["date_calcul"].date() < datetime.date.today():
        alerte = Calculer()
        Enregistrer(alerte)

    if not alerte["items"]:
        return None
    return alerte


def Masquer(request=None):
    from core.utils import utils_parametres
    from dateutil.relativedelta import relativedelta
    date_fin = datetime.date.today() + relativedelta(months=DUREE_MASQUAGE_MOIS)
    utils_parametres.Set(nom="masquer_alerte_jusqu", categorie=CATEGORIE_PARAMETRES, utilisateur=request.user, valeur=date_fin.strftime("%Y-%m-%d"))
