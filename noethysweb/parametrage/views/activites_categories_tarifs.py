# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.db.models import Count
from core.views.mydatatableview import MyDatatable, columns
from core.views import crud
from parametrage.views.activites import Onglet
from core.models import CategorieTarif
from parametrage.forms.activites_categories_tarifs import Formulaire
from django.db.models import Q


class Page(Onglet):
    model = CategorieTarif
    url_liste = "activites_categories_tarifs_liste"
    url_ajouter = "activites_categories_tarifs_ajouter"
    url_modifier = "activites_categories_tarifs_modifier"
    url_supprimer = "activites_categories_tarifs_supprimer"
    description_liste = """Vous pouvez saisir ici une catégorie de tarif pour l'activité. Exemples : Commune, Hors commune, Tarif réduit, Famille nombreuse... 
                        Il est obligatoirement de créer au moins une catégorie de tarif. Si vous n'avez qu'une seule catégorie de tarif, créez simplement une
                        catégorie nommée par exemple 'Catégorie par défaut'."""
    description_saisie = "Saisissez toutes les informations concernant la catégorie de tarif à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une catégorie de tarif"
    objet_pluriel = "des catégories de tarifs"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Catégories de tarifs"
        context['onglet_actif'] = "categories_tarifs"
        context['boutons_liste'] = [
            {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'idactivite': self.Get_idactivite()}), "icone": "fa fa-plus"},
        ]
        return context

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idactivite au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idactivite"] = self.Get_idactivite()
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idactivite': self.Get_idactivite()})



class Liste(Page, crud.Liste):
    model = CategorieTarif
    template_name = "parametrage/activite_liste.html"

    def get_queryset(self):
        return CategorieTarif.objects.filter(Q(activite=self.Get_idactivite()) & self.Get_filtres("Q")).annotate(nbre_inscrits=Count("inscription"))

    class datatable_class(MyDatatable):
        filtres = ['idcategorie_tarif', 'nom']
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        nbre_inscrits = columns.TextColumn("Inscrits", sources="nbre_inscrits")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idcategorie_tarif', 'nom', 'nbre_inscrits']
            ordering = ['nom']

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idactivite dans les boutons d'actions """
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.activite.idactivite, instance.pk])),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.activite.idactivite, instance.pk])),
            ]
            return self.Create_boutons_actions(html)



class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "parametrage/activite_edit.html"

class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "parametrage/activite_edit.html"

class Supprimer(Page, crud.Supprimer):
    template_name = "parametrage/activite_delete.html"
    manytomany_associes = [("tarif(s)", "tarif_categories_tarifs")]
