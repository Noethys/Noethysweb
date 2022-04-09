# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import PesModele
from parametrage.forms.modeles_pes import Formulaire, Formulaire_creation
from django.http import HttpResponseRedirect



class Page(crud.Page):
    model = PesModele
    url_liste = "modeles_pes_liste"
    url_ajouter = "modeles_pes_creer"
    url_modifier = "modeles_pes_modifier"
    url_supprimer = "modeles_pes_supprimer"
    description_liste = "Voici ci-dessous la liste des modèles d'exports vers le Trésor Public."
    description_saisie = "Saisissez toutes les informations concernant le modèle à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un modèle d'export"
    objet_pluriel = "des modèles d'exports"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = PesModele

    def get_queryset(self):
        return PesModele.objects.filter(self.Get_filtres("Q"))

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
        context['box_introduction'] = "Vous devez sélectionner un format d'export."
        return context

    def post(self, request, **kwargs):
        return HttpResponseRedirect(reverse_lazy("modeles_pes_ajouter", kwargs={"format": request.POST.get("format")}))

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
