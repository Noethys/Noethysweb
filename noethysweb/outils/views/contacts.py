# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Contact
from outils.forms.contacts import Formulaire



class Page(crud.Page):
    model = Contact
    url_liste = "contacts_liste"
    url_ajouter = "contacts_ajouter"
    url_modifier = "contacts_modifier"
    url_supprimer = "contacts_supprimer"
    description_liste = "Voici ci-dessous la liste des contacts."
    description_saisie = "Saisissez toutes les informations concernant le contact à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un contact"
    objet_pluriel = "des contacts"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = Contact

    def get_queryset(self):
        return Contact.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idcontact", "nom", "prenom", "rue_resid", "cp_resid", "ville_resid", "tel_domicile", "tel_mobile", "mail"]

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idcontact", "nom", "prenom", "rue_resid", "cp_resid", "ville_resid", "tel_domicile", "tel_mobile", "mail"]
            #hidden_columns = = ["idcontact"]
            ordering = ["nom", "prenom"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass
