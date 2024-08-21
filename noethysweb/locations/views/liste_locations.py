# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.urls import reverse_lazy, reverse
from django.db.models import Q
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Location
from core.utils import utils_parametres


class Page(crud.Page):
    model = Location
    url_liste = "locations_liste"
    description_liste = "Voici ci-dessous la liste des locations."
    description_saisie = "Saisissez toutes les informations concernant la location à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une location"
    objet_pluriel = "des locations"
    url_supprimer_plusieurs = "locations_supprimer_plusieurs"


class Liste(Page, crud.Liste):
    model = Location
    template_name = "locations/liste_locations.html"

    def get_queryset(self):
        self.afficher_locations_actuelles = utils_parametres.Get(nom="afficher_locations_actuelles", categorie="liste_locations", utilisateur=self.request.user, valeur=True)
        conditions = Q()
        if self.afficher_locations_actuelles:
            conditions &= Q(date_debut__lte=datetime.datetime.now()) & (Q(date_fin__isnull=True) | Q(date_fin__gte=datetime.datetime.now()))
        return Location.objects.select_related("famille", "produit").filter(self.Get_filtres("Q"), conditions)

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['active_checkbox'] = True
        context['afficher_locations_actuelles'] = self.afficher_locations_actuelles
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
            url_supprimer = "famille_locations_supprimer" if not instance.serie else "famille_locations_supprimer_occurence"
            html = [
                self.Create_bouton_modifier(url=reverse("famille_locations_modifier", kwargs={"idfamille": instance.famille_id, "pk": instance.pk})),
                self.Create_bouton_supprimer(url=reverse(url_supprimer, kwargs={"idfamille": instance.famille_id, "pk": instance.pk})),
                self.Create_bouton_imprimer(url=reverse("famille_voir_location", kwargs={"idfamille": instance.famille_id, "idlocation": instance.pk}), title="Imprimer ou envoyer par email la location"),
            ]
            return self.Create_boutons_actions(html)


class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
    pass
