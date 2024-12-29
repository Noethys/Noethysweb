# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import ComptaBudget
from parametrage.forms.budgets import Formulaire, FORMSET_CATEGORIES


class Page(crud.Page):
    model = ComptaBudget
    url_liste = "budgets_liste"
    url_ajouter = "budgets_ajouter"
    url_modifier = "budgets_modifier"
    url_supprimer = "budgets_supprimer"
    description_liste = "Voici ci-dessous la liste des budgets."
    description_saisie = "Saisissez toutes les informations concernant le budget à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un budget"
    objet_pluriel = "des budgets"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        if hasattr(self, "object"):
            form_kwargs={"request": self.request}
            context["formset_categories"] = FORMSET_CATEGORIES(self.request.POST, instance=self.object, form_kwargs={"request": self.request}) if self.request.POST else FORMSET_CATEGORIES(instance=self.object, form_kwargs={"request": self.request})
        return context

    def form_valid(self, form):
        if getattr(self, "verbe_action", None) == "Supprimer":
            return super().form_valid(form)

        formset_categories = FORMSET_CATEGORIES(self.request.POST, instance=self.object, form_kwargs={"request": self.request})
        if not formset_categories.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        # Sauvegarde
        self.object = form.save()

        # Sauvegarde des catégories
        if formset_categories.is_valid():
            for formline in formset_categories.forms:
                if formline.cleaned_data.get('DELETE') and form.instance.pk and formline.instance.pk:
                    formline.instance.delete()
                if formline.cleaned_data and not formline.cleaned_data.get('DELETE'):
                    instance = formline.save(commit=False)
                    instance.budget = self.object
                    instance.save()

        return super().form_valid(form)


class Liste(Page, crud.Liste):
    model = ComptaBudget

    def get_queryset(self):
        return ComptaBudget.objects.filter(self.Get_filtres("Q"), self.Get_condition_structure())

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idbudget", "nom", "observations", "date_debut", "date_fin"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idbudget", "nom", "date_debut", "date_fin", "observations"]
            ordering = ["nom"]
            processors = {
                "date_debut": helpers.format_date("%d/%m/%Y"),
                "date_fin": helpers.format_date("%d/%m/%Y"),
            }


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    pass
