# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import PrelevementsModele
from parametrage.forms.modeles_prelevements import Formulaire, Formulaire_creation


class Page(crud.Page):
    model = PrelevementsModele
    url_liste = "modeles_prelevements_liste"
    url_ajouter = "modeles_prelevements_creer"
    url_modifier = "modeles_prelevements_modifier"
    url_supprimer = "modeles_prelevements_supprimer"
    description_liste = "Les modèles de prélèvements définissent les paramètres des fichiers de prélèvements SEPA transmis à la banque ou à la trésorerie : compte bancaire, format, perception, libellés... Ils sont utilisés depuis le menu Facturation pour générer les lots de prélèvements."
    description_saisie = "Renseignez le compte bancaire, les options et les libellés des prélèvements, puis cliquez sur le bouton Enregistrer."
    objet_singulier = "un modèle de prélèvement"
    objet_pluriel = "des modèles de prélèvements"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = PrelevementsModele

    def get_queryset(self):
        return PrelevementsModele.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idmodele", "nom", "format"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        format = columns.TextColumn("Format", sources="format", processor='Get_format')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idmodele", "nom", "format"]
            ordering = ["nom"]

        def Get_format(self, instance, **kwargs):
            return instance.get_format_display()


class Creer(Page, crud.Ajouter):
    form_class = Formulaire_creation
    template_name = "core/crud/edit.html"

    def get_context_data(self, **kwargs):
        context = super(Creer, self).get_context_data(**kwargs)
        context['box_introduction'] = "Sélectionnez le format de prélèvement : 'Secteur privé' pour une association ou 'Secteur public DFT' pour une collectivité, puis cliquez sur le bouton Valider."
        return context

    def post(self, request, **kwargs):
        return HttpResponseRedirect(reverse_lazy("modeles_prelevements_ajouter", kwargs={"format": request.POST.get("format")}))


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["format"] = self.kwargs.get("format", None)
        return form_kwargs


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    pass
