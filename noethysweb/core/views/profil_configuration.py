# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, importlib
from django.http import JsonResponse
from django.db.models import Q
from core.models import Parametre
from core.utils import utils_parametres

# Couples (catégorie, module) déclarés par les widgets Profil_configuration : seuls ces modules peuvent être importés
MODULES_AUTORISES = set()

# Mémorisation du profil par défaut de chaque utilisateur (nom = catégorie du profil)
CATEGORIE_PROFIL_DEFAUT = "profil_configuration_defaut"


def Get_conditions_acces(request=None, categorie=""):
    """ Profils visibles par l'utilisateur : les siens, ceux de ses structures et ceux de tous les utilisateurs """
    conditions = Q(categorie=categorie)
    conditions &= (Q(utilisateur=request.user) | Q(utilisateur__isnull=True))
    conditions &= (Q(structure__in=request.user.structures.all()) | Q(structure__isnull=True))
    return conditions


def Get_profil(request=None, categorie="", idprofil=None):
    """ Renvoie le profil s'il est accessible à l'utilisateur, sinon None """
    try:
        return Parametre.objects.filter(Get_conditions_acces(request, categorie), pk=int(idprofil)).first()
    except (TypeError, ValueError):
        return None


def Get_id_profil_defaut(request=None, categorie=""):
    """ Identifiant du profil choisi par défaut par l'utilisateur (ou None) """
    parametre = Parametre.objects.filter(categorie=CATEGORIE_PROFIL_DEFAUT, nom=categorie, utilisateur=request.user).first()
    try:
        idprofil = int(parametre.parametre) if parametre and parametre.parametre else None
    except ValueError:
        idprofil = None
    return idprofil if idprofil and Get_profil(request, categorie, idprofil) else None


def Get_profil_defaut(request=None, categorie="edition_liste_conso"):
    """ Profil choisi par défaut par l'utilisateur, sinon le premier profil accessible """
    idprofil = Get_id_profil_defaut(request, categorie)
    if idprofil:
        return Get_profil(request, categorie, idprofil)
    return Parametre.objects.filter(Get_conditions_acces(request, categorie)).order_by("nom").first()


def Get_portee(parametre=None):
    if parametre.utilisateur_id:
        return "moi"
    if parametre.structure_id:
        return "structure"
    return "tous"


def Modifier_profil_configuration(request):
    action = request.POST.get("action")
    categorie = request.POST.get("categorie")
    module = request.POST.get("module")
    idprofil = request.POST.get("id")

    # Le couple catégorie / module doit avoir été déclaré par un widget
    if (categorie, module) not in MODULES_AUTORISES:
        return JsonResponse({"erreur": "Catégorie de profil inconnue"}, status=401)

    try:
        donnees_profil = json.loads(request.POST.get("donnees_profil") or "{}")
    except ValueError:
        donnees_profil = {}

    # Formatage des données de profil
    nom = (donnees_profil.get("profil_nom") or "").strip()[:200]
    portee = donnees_profil.get("profil_utilisateurs")
    utilisateur = request.user if portee == "moi" else None
    idstructure = None
    if portee == "structure":
        structure = request.user.structures.filter(pk=donnees_profil.get("profil_structure") or 0).first()
        if not structure:
            return JsonResponse({"erreur": "Veuillez sélectionner une de vos structures"}, status=401)
        idstructure = structure.pk
    if action in ("ajouter", "modifier") and not nom:
        return JsonResponse({"erreur": "Veuillez saisir un nom pour ce profil"}, status=401)

    # Toutes les actions sur un profil existant nécessitent qu'il soit accessible à l'utilisateur
    parametre = None
    if action in ("ouvrir", "modifier", "supprimer", "enregistrer", "defaut") and not (action == "defaut" and not idprofil):
        parametre = Get_profil(request, categorie, idprofil)
        if not parametre:
            return JsonResponse({"erreur": "Ce profil n'existe pas ou ne vous est pas accessible"}, status=401)

    # Ouvrir un profil
    if action == "ouvrir":
        return JsonResponse({"action": action, "id": parametre.pk, "profil_nom": parametre.nom, "profil_utilisateurs": Get_portee(parametre),
                             "profil_structure": parametre.structure_id, "defaut": Get_id_profil_defaut(request, categorie) == parametre.pk})

    # Ajouter un profil
    if action == "ajouter":
        parametre = Parametre.objects.create(categorie=categorie, nom=nom, utilisateur=utilisateur, structure_id=idstructure)
        resultat = Enregistrer(request=request, module=module, parametre=parametre)
        if resultat:
            parametre.delete()
            return resultat
        Memoriser_defaut(request, categorie, parametre.pk, donnees_profil.get("defaut"))
        return JsonResponse({"action": action, "id": parametre.pk, "profil_nom": parametre.nom, "portee": Get_portee(parametre)})

    # Modifier un profil (nom et partage)
    if action == "modifier":
        parametre.nom = nom
        parametre.utilisateur = utilisateur
        parametre.structure_id = idstructure
        parametre.save()
        Memoriser_defaut(request, categorie, parametre.pk, donnees_profil.get("defaut"))
        return JsonResponse({"action": action, "id": parametre.pk, "profil_nom": parametre.nom, "portee": Get_portee(parametre)})

    # Supprimer un profil
    if action == "supprimer":
        idprofil = parametre.pk
        parametre.delete()
        return JsonResponse({"action": action, "id": idprofil})

    # Enregistrer les paramètres actuels dans le profil
    if action == "enregistrer":
        resultat = Enregistrer(request=request, module=module, parametre=parametre)
        if resultat:
            return resultat
        return JsonResponse({"action": action, "id": parametre.pk})

    # Définir (ou retirer) le profil par défaut
    if action == "defaut":
        utils_parametres.Set(nom=categorie, categorie=CATEGORIE_PROFIL_DEFAUT, utilisateur=request.user, valeur=parametre.pk if parametre else None)
        return JsonResponse({"action": action, "id": parametre.pk if parametre else None})

    return JsonResponse({"erreur": "Action inconnue"}, status=401)


def Memoriser_defaut(request=None, categorie="", idprofil=None, defaut=None):
    """ Coche ou décoche le profil par défaut depuis la fenêtre d'enregistrement """
    if defaut is None:
        return
    id_actuel = Get_id_profil_defaut(request, categorie)
    if defaut:
        utils_parametres.Set(nom=categorie, categorie=CATEGORIE_PROFIL_DEFAUT, utilisateur=request.user, valeur=idprofil)
    elif id_actuel == idprofil:
        utils_parametres.Set(nom=categorie, categorie=CATEGORIE_PROFIL_DEFAUT, utilisateur=request.user, valeur=None)


def Enregistrer(request=None, module="", parametre=None):
    """ Mémorise les paramètres du profil """
    donnees = request.POST.get("donnees")

    # Récupération des paramètres à sauvegarder dans le profil (module déjà vérifié dans MODULES_AUTORISES)
    module = importlib.import_module(module)
    data = module.get_data_profil(donnees, request=request)

    # S'il y a une erreur, on retourne l'erreur au format JsonResponse
    if isinstance(data, JsonResponse):
        return data

    # Enregistrement des paramètres
    parametre.parametre = json.dumps(data)
    parametre.save()
    return None
