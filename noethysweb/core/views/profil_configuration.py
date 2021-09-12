# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, importlib
from django.http import JsonResponse, QueryDict
from django.db.models import Q
from core.models import Parametre


def Get_profil_defaut(request=None, categorie="edition_liste_conso"):
    conditions = Q(categorie=categorie)
    conditions &= (Q(utilisateur=request.user) | Q(utilisateur__isnull=True))
    conditions &= (Q(structure__in=request.user.structures.all()) | Q(structure__isnull=True))
    return Parametre.objects.filter(conditions).order_by("nom").first()


def Modifier_profil_configuration(request):
    action = request.POST.get("action")
    categorie = request.POST.get("categorie")
    module = request.POST.get("module")
    idprofil = request.POST.get("id")
    donnees_profil = json.loads(request.POST.get("donnees_profil"))

    # Formatage des données de profil
    nom = donnees_profil["profil_nom"]
    utilisateur = request.user if donnees_profil["profil_utilisateurs"] == "moi" else None
    idstructure = donnees_profil["profil_structure"] if donnees_profil["profil_utilisateurs"] == "structure" else None

    # Ouvrir un profil
    if action == "ouvrir":
        parametre = Parametre.objects.get(idparametre=int(idprofil))
        profil_utilisateurs = "moi" if parametre.utilisateur else "structure"
        return JsonResponse({"action": action, "id": parametre.pk, "profil_nom": parametre.nom, "profil_utilisateurs": profil_utilisateurs, "profil_structure": parametre.structure_id})

    # Ajouter un profil
    if action == "ajouter":
        parametre = Parametre.objects.create(categorie=categorie, nom=nom, utilisateur=utilisateur, structure_id=idstructure)
        Enregistrer(request=request, module=module, idprofil=parametre.pk)
        return JsonResponse({"action": action, "id": parametre.pk, "profil_nom": parametre.nom})

    # Modifier un profil
    if action == "modifier":
        parametre = Parametre.objects.get(idparametre=int(idprofil))
        parametre.nom = nom
        parametre.utilisateur = utilisateur
        parametre.structure_id = idstructure
        parametre.save()
        return JsonResponse({"action": action, "id": parametre.pk, "profil_nom": parametre.nom})

    # Supprimer un profil
    if action == "supprimer":
        try:
            parametre = Parametre.objects.get(idparametre=int(idprofil))
            parametre.delete()
            return JsonResponse({"action": action, "id": int(idprofil)})
        except:
            return JsonResponse({"erreur": "Vous ne pouvez pas supprimer ce profil"}, status=401)

    if action == "enregistrer":
        Enregistrer(request=request, module=module, idprofil=idprofil)
        return JsonResponse({"action": action})

    return JsonResponse({"erreur": "Erreur !"}, status=401)


def Enregistrer(request=None, module="", idprofil=None):
    """ Mémorise les paramètres du profil """
    donnees = QueryDict(request.POST.get("donnees"))

    # Récupération des paramètres à sauvegarder dans le profil
    module = importlib.import_module(module)
    data = module.get_data_profil(donnees, request=request)

    # Enregistrement des paramètres
    parametre = Parametre.objects.get(idparametre=int(idprofil))
    parametre.parametre = json.dumps(data)
    parametre.save()
