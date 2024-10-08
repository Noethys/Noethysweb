# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.db.models import Q
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Location
from core.utils import utils_dates
from locations.forms.locations_choix_modele import Formulaire as Form_modele


def Impression_pdf(request):
    # Récupération des locations cochées
    locations_cochees = json.loads(request.POST.get("locations_cochees"))
    if not locations_cochees:
        return JsonResponse({"erreur": "Veuillez cocher au moins une location dans la liste"}, status=401)

    # Récupération du modèle de document
    valeurs_form_modele = json.loads(request.POST.get("form_modele"))
    form_modele = Form_modele(valeurs_form_modele)
    if not form_modele.is_valid():
        return JsonResponse({"erreur": "Veuillez sélectionner un modèle de document"}, status=401)

    dict_options = form_modele.cleaned_data

    # Création du PDF
    from locations.utils import utils_locations
    locations = utils_locations.Locations()
    resultat = locations.Impression(liste_locations=locations_cochees, dict_options=dict_options)
    if not resultat:
        return JsonResponse({"success": False}, status=401)
    return JsonResponse({"nom_fichier": resultat["nom_fichier"]})


class Page(crud.Page):
    model = Location
    url_liste = "locations_impression"
    menu_code = "locations_impression"


class Liste(Page, crud.Liste):
    template_name = "locations/locations_impression.html"
    model = Location

    def get_queryset(self):
        return Location.objects.select_related("famille", "produit").filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Gestion des locations"
        context['box_titre'] = "Imprimer des locations"
        context['box_introduction'] = "Cochez des locations, sélectionnez si besoin un modèle de document puis cliquez sur le bouton Aperçu."
        context['onglet_actif'] = "locations_impression"
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        context["hauteur_table"] = "400px"
        context['form_modele'] = Form_modele()
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:famille", "idlocation", "nom_produit", "date_debut", "date_fin"]
        check = columns.CheckBoxSelectColumn(label="")
        nom_produit = columns.TextColumn("Nom", sources=["produit__nom"], processor='Get_nom_produit')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        famille = columns.TextColumn("Famille", sources=['famille__nom'])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idlocation", "nom_produit", "date_debut", "date_fin", "famille"]
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y %H:%M'),
                'date_fin': helpers.format_date('%d/%m/%Y %H:%M'),
            }
            labels = {
                "date_debut": "Début",
                "date_fin": "Fin",
            }
            ordering = ["date_debut"]

        def Get_nom_produit(self, instance, *args, **kwargs):
            return instance.produit.nom

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idindividu dans les boutons d'actions """
            html = [
                self.Create_bouton_imprimer(url=reverse("famille_voir_location", kwargs={"idfamille": instance.famille_id, "idlocation": instance.pk}), title="Imprimer ou envoyer par email la location"),
            ]
            return self.Create_boutons_actions(html)
