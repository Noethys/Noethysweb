# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.db.models import Q
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Mandat
from fiche_famille.forms.famille_mandat import Formulaire
from fiche_famille.views.famille import Onglet


class Page(Onglet):
    model = Mandat
    url_liste = "famille_mandats_liste"
    url_ajouter = "famille_mandats_ajouter"
    url_modifier = "famille_mandats_modifier"
    url_supprimer = "famille_mandats_supprimer"
    description_liste = "Saisissez ici les mandats de prélèvement SEPA de la famille."
    description_saisie = "Saisissez toutes les informations concernant le mandat et cliquez sur le bouton Enregistrer."
    objet_singulier = "un mandat"
    objet_pluriel = "des mandats"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        if not hasattr(self, "verbe_action"):
            context['box_titre'] = "Prélèvement"
        context['onglet_actif'] = "reglements"
        context['boutons_liste'] = [
            {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'idfamille': self.kwargs.get('idfamille', None)}), "icone": "fa fa-plus"},
        ]
        return context

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idfamille"] = self.Get_idfamille()
        return form_kwargs

    def get_success_url(self):
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idfamille': self.kwargs.get('idfamille', None)})


class Liste(Page, crud.Liste):
    model = Mandat
    template_name = "fiche_famille/famille_liste.html"

    def get_queryset(self):
        return Mandat.objects.filter(Q(famille__pk=self.Get_idfamille()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ["idmandat", "date", "rum", "iban", "bic", "actif", "sequence"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        actif = columns.TextColumn("Etat", sources=["actif"], processor='Get_actif')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idmandat", "date", "rum", "iban", "bic", "actif", "sequence"]
            ordering = ["date"]
            processors = {
                'date': helpers.format_date('%d/%m/%Y'),
            }
            hidden_columns = ["sequence"]

        def Get_actif(self, instance, *args, **kwargs):
            return "<small class='badge badge-success'>Activé</small>" if instance.actif else "<small class='badge badge-danger'>Désactivé</small>"

        def Get_actions_speciales(self, instance, *args, **kwargs):
            view = kwargs["view"]
            kwargs = view.kwargs
            kwargs["pk"] = instance.pk
            html = [
                self.Create_bouton_modifier(url=reverse(view.url_modifier, kwargs=kwargs)),
                self.Create_bouton_supprimer(url=reverse(view.url_supprimer, kwargs=kwargs)),
                self.Create_bouton_imprimer(url=reverse("famille_voir_mandat", kwargs={"idfamille": kwargs["idfamille"], "idmandat": instance.pk}), title="Imprimer ou envoyer par email le mandat"),
            ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "fiche_famille/famille_edit.html"
    mode = "fiche_famille"

class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "fiche_famille/famille_edit.html"
    mode = "fiche_famille"

class Supprimer(Page, crud.Supprimer):
    template_name = "fiche_famille/famille_delete.html"
