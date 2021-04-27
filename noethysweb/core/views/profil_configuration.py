# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from core.models import Parametre
from django.http import JsonResponse, QueryDict
import json, importlib



def Modifier_profil_configuration(request):
    action = request.POST.get("action")
    categorie = request.POST.get("categorie")
    module = request.POST.get("module")
    idprofil = request.POST.get("id")
    nom = request.POST.get("valeur")

    # Ajouter un profil
    if action == "ajouter":
        parametre = Parametre.objects.create(categorie=categorie, nom=nom)
        return JsonResponse({"action": action, "id": parametre.pk, "valeur": parametre.nom})

    # Modifier un profil
    if action == "modifier":
        parametre = Parametre.objects.get(idparametre=int(idprofil))
        parametre.nom = nom
        parametre.save()
        return JsonResponse({"action": action, "id": parametre.pk, "valeur": parametre.nom})

    # Supprimer un profil
    if action == "supprimer":
        try:
            parametre = Parametre.objects.get(idparametre=int(idprofil))
            parametre.delete()
            return JsonResponse({"action": action, "id": int(idprofil)})
        except:
            return JsonResponse({"erreur": "Vous ne pouvez pas supprimer ce profil"}, status=401)

    # Enregistrer les données associées au profil
    if action == "enregistrer":
        donnees = QueryDict(request.POST.get("donnees"))

        # Récupération des paramètres à sauvegarder dans le profil
        module = importlib.import_module(module)
        data = module.get_data_profil(donnees)

        # Enregistrement des paramètres
        parametre = Parametre.objects.get(idparametre=int(idprofil))
        parametre.parametre = json.dumps(data)
        parametre.save()
        return JsonResponse({"action": action})

    return JsonResponse({"erreur": "Erreur !"}, status=401)
