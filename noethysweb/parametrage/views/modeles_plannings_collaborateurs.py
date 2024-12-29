# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.template.context_processors import csrf
from django.contrib import messages
from crispy_forms.utils import render_crispy_form
from core.views.mydatatableview import MyDatatable, columns
from core.views import crud
from core.models import ModelePlanningCollaborateur, LigneModelePlanningCollaborateur
from parametrage.forms.modeles_plannings_collaborateurs import Formulaire
from parametrage.forms.lignes_modeles_plannings_collaborateurs import Formulaire as Formulaire_ligne


def Get_form_ligne(request):
    action = request.POST.get("action", None)
    index = request.POST.get("index", None)

    initial_data = {}
    if "valeur" in request.POST:
        initial_data = json.loads(request.POST["valeur"])
        initial_data["index"] = index

    # Création et rendu html du formulaire
    if action in ("ajouter", "modifier"):
        form = Formulaire_ligne(request=request, initial=initial_data)
        return JsonResponse({"form_html": render_crispy_form(form, context=csrf(request))})

    # Validation du formulaire
    form = Formulaire_ligne(request.POST, request=request)
    if not form.is_valid():
        messages_erreurs = ["<b>%s</b> : %s " % (field.title(), erreur[0].message) for field, erreur in form.errors.as_data().items()]
        return JsonResponse({"erreur": messages_erreurs}, status=401)

    # Transformation en chaîne
    dict_retour = {
        "idligne": form.cleaned_data["idligne"],
        "jour": form.cleaned_data["jour"],
        "periode": form.cleaned_data["periode"],
        "heure_debut": str(form.cleaned_data["heure_debut"]),
        "heure_fin": str(form.cleaned_data["heure_fin"]),
        "type_evenement": form.cleaned_data["type_evenement"].pk,
        "titre": form.cleaned_data["titre"],
    }
    return JsonResponse({"valeur": dict_retour, "index": form.cleaned_data["index"]})


class Page(crud.Page):
    model = ModelePlanningCollaborateur
    url_liste = "modeles_plannings_collaborateurs_liste"
    url_ajouter = "modeles_plannings_collaborateurs_ajouter"
    url_modifier = "modeles_plannings_collaborateurs_modifier"
    url_supprimer = "modeles_plannings_collaborateurs_supprimer"
    description_liste = "Voici ci-dessous la liste des modèles de plannings pour les collaborateurs."
    description_saisie = "Saisissez toutes les informations concernant le modèle de planning à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un modèle de planning"
    objet_pluriel = "des modèles de planning"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]

    def form_valid(self, form):
        if getattr(self, "verbe_action", None) == "Supprimer":
            return super().form_valid(form)

        # Récupération des lignes
        lignes = json.loads(form.cleaned_data.get("lignes", "[]"))
        if not lignes:
            messages.add_message(self.request, messages.ERROR, "Vous devez saisir au moins un évènement")
            return self.render_to_response(self.get_context_data(form=form))

        # Sauvegarde
        self.object = form.save()

        # Récupération des lignes existantes
        lignes_existantes = list(LigneModelePlanningCollaborateur.objects.filter(modele=self.object))

        # Sauvegarde des lignes
        for ligne in lignes:
            idligne = ligne["idligne"] if ligne["idligne"] else None
            LigneModelePlanningCollaborateur.objects.update_or_create(pk=idligne, defaults={"modele": self.object,
                "jour": ligne["jour"], "periode": ligne["periode"], "heure_debut": ligne["heure_debut"], "heure_fin": ligne["heure_fin"],
                "type_evenement_id": ligne["type_evenement"], "titre": ligne["titre"]})

        # Suppression des lignes supprimées
        for ligne in lignes_existantes:
            if ligne.pk not in [int(item["idligne"]) for item in lignes if item["idligne"]]:
                ligne.delete()

        return super().form_valid(form)


class Liste(Page, crud.Liste):
    model = ModelePlanningCollaborateur

    def get_queryset(self):
        return ModelePlanningCollaborateur.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idmodele", "nom", "observations"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idmodele", "nom", "observations"]
            ordering = ["nom"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    pass
