# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, logging, time
logger = logging.getLogger(__name__)
from django.http import JsonResponse
from core.views.mydatatableview import MyDatatable, columns
from core.views import crud
from core.models import Rattachement
from core.utils import utils_parametres
from individus.forms.edition_renseignements import Formulaire


def Generer_pdf(request):
    time.sleep(1)

    # Récupération des options
    valeurs_form_options = json.loads(request.POST.get("form_options"))
    form = Formulaire(valeurs_form_options, request=request)
    if not form.is_valid():
        return JsonResponse({"erreur": "Veuillez compléter les paramètres"}, status=401)
    options = form.cleaned_data

    # Récupération des rattachements cochés
    rattachements = json.loads(request.POST.get("rattachements"))
    if not rattachements:
        return JsonResponse({"erreur": "Veuillez cocher au moins une ligne dans la liste"}, status=401)
    options["rattachements"] = rattachements

    # Mémorisation des paramètres
    utils_parametres.Set_categorie(categorie="edition_renseignements", utilisateur=request.user, parametres={
        "bonus_titre": form.cleaned_data["bonus_titre"], "bonus_texte": form.cleaned_data["bonus_texte"]})

    # Création du PDF
    from individus.utils import utils_impression_renseignements
    impression = utils_impression_renseignements.Impression(titre="Renseignements", dict_donnees=options)
    if impression.erreurs:
        return JsonResponse({"erreur": impression.erreurs[0]}, status=401)
    nom_fichier = impression.Get_nom_fichier()
    return JsonResponse({"nom_fichier": nom_fichier})


class Page(crud.Page):
    model = Rattachement
    url_liste = "edition_renseignements"
    menu_code = "edition_renseignements"


class Liste(Page, crud.Liste):
    template_name = "individus/edition_renseignements.html"
    model = Rattachement

    def get_queryset(self):
        return Rattachement.objects.select_related("famille", "individu").filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context["page_titre"] = "Edition des fiches de renseignements"
        context["box_titre"] = "Edition des fiches de renseignements"
        context["box_introduction"] = "Cochez les individus souhaités, précisez si besoin les options et cliquez sur le bouton Générer le PDF. Utilisez le bouton Filtrer pour affiner la liste d'individus."
        context["onglet_actif"] = "edition_renseignements"
        context["impression_introduction"] = ""
        context["impression_conclusion"] = ""
        context["active_checkbox"] = True
        context["bouton_supprimer"] = False
        context["hauteur_table"] = "400px"
        context["form_options"] = Formulaire(request=self.request)
        context["afficher_menu_brothers"] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:famille", "igenerique:individu"]
        check = columns.CheckBoxSelectColumn(label="")
        individu = columns.CompoundColumn("Individu", sources=["individu__nom", "individu__prenom"])
        famille = columns.TextColumn("Famille", sources=["famille__nom"])
        rue_resid = columns.TextColumn("Rue", sources=None, processor="Get_rue_resid")
        cp_resid = columns.TextColumn("CP", sources=None, processor="Get_cp_resid")
        ville_resid = columns.TextColumn("Ville", sources=None, processor="Get_ville_resid")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idrattachement", "individu", "famille", "rue_resid", "cp_resid", "ville_resid"]
            ordering = ["individu__nom", "individu__prenom"]

        def Get_rue_resid(self, instance, *args, **kwargs):
            return instance.individu.rue_resid

        def Get_cp_resid(self, instance, *args, **kwargs):
            return instance.individu.cp_resid

        def Get_ville_resid(self, instance, *args, **kwargs):
            return instance.individu.ville_resid
