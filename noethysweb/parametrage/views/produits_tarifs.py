# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.db.models import Q
from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns
from core.views import crud
from core.models import TarifProduit, Produit
from parametrage.forms.produits_tarifs import Formulaire


class Page(crud.Page):
    model = TarifProduit
    url_liste = "produits_tarifs_liste"
    url_ajouter = "produits_tarifs_ajouter"
    url_modifier = "produits_tarifs_modifier"
    url_supprimer = "produits_tarifs_supprimer"
    description_liste = "Vous pouvez saisir ici des tarifs avancés pour un produit."
    description_saisie = "Saisissez toutes les informations concernant le tarif et cliquez sur le bouton Enregistrer."
    objet_singulier = "un tarif de produit"
    objet_pluriel = "des tarifs d'un produit"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        produit = Produit.objects.get(pk=self.Get_produit())
        context['box_titre'] = "Tarifs avancés du produit %s" % produit.nom
        context['url_liste'] = self.url_liste
        context['boutons_liste'] = [
            {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'idproduit': self.Get_produit()}), "icone": "fa fa-plus"},
            {"label": "Retour à la liste des produits", "classe": "btn btn-default", "href": reverse_lazy("produits_liste"), "icone": "fa fa-arrow-circle-o-left"},
        ]
        return context

    def Get_produit(self):
        return self.kwargs.get('idproduit', None)

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idproduit"] = self.Get_produit()
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idproduit': self.Get_produit()})



class Liste(Page, crud.Liste):
    model = TarifProduit

    def get_queryset(self):
        return TarifProduit.objects.filter(Q(produit=self.Get_produit()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        return context

    class datatable_class(MyDatatable):
        filtres = ['idtarif', 'description', 'methode']
        methode = columns.TextColumn("Méthode", sources=["methode"], processor='Get_methode')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idtarif', 'description', 'methode']

        def Get_methode(self, instance, *args, **kwargs):
            return instance.get_methode_display()

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.produit_id, instance.pk])),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.produit_id, instance.pk])),
            ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Ajouter, self).get_context_data(**kwargs)
        produit = Produit.objects.get(pk=self.Get_produit())
        context['box_titre'] = "Tarif avancé pour le produit %s" % produit.nom
        return context


class Modifier(Page, crud.Modifier):
    form_class = Formulaire

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Modifier, self).get_context_data(**kwargs)
        produit = Produit.objects.get(pk=self.Get_produit())
        context['box_titre'] = "Tarif avancé pour le produit %s" % produit.nom
        return context


class Supprimer(Page, crud.Supprimer):
    pass
