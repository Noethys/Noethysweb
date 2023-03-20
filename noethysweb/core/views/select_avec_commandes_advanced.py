# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import importlib
from django.apps import apps
from django.http import JsonResponse
from django.template.context_processors import csrf
from crispy_forms.utils import render_crispy_form


def Modifier(request):
    action = request.POST.get("action", None)
    champ_nom = request.POST.get("champ_nom", "nom")

    # Récupération du formulaire
    module = importlib.import_module(request.POST.get("module_form", None))
    module_form = getattr(module, "Formulaire")

    # Récupération de l'instance
    model = apps.get_model("core", module_form.Meta.model.__name__)
    instance = model.objects.get(pk=int(request.POST["pk"])) if request.POST.get("pk", None) else None

    # Suppression
    if action == "supprimer":
        try:
            instance.delete()
        except:
            return JsonResponse({"erreur": "Vous ne pouvez pas supprimer cette donnée"}, status=401)
        return JsonResponse({"action": action, "id": int(request.POST["pk"]), "nom": getattr(instance, champ_nom)})

    # Création et rendu html du formulaire
    if action in ("ajouter", "modifier"):
        form = module_form(request=request, instance=instance)
        del form.helper[0]
        return JsonResponse({"form_html": render_crispy_form(form, context=csrf(request))})

    # Validation du formulaire
    form = module_form(request.POST, request=request)
    if not form.is_valid():
        messages_erreurs = ["%s : %s" % (field.title(), erreur[0].message) for field, erreur in form.errors.as_data().items()]
        return JsonResponse({"erreur": messages_erreurs}, status=401)

    objet = form.save()
    return JsonResponse({"action": "modifier" if instance else "ajouter", "id": objet.pk, "nom": getattr(objet, champ_nom)})
