# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import SMS


class Page(crud.Page):
    model = SMS
    url_liste = "sms_liste"
    url_modifier = "editeur_sms"
    url_supprimer = "sms_supprimer"
    url_supprimer_plusieurs = "sms_supprimer_plusieurs"
    description_liste = "Voici ci-dessous la liste des SMS enregistrés."
    objet_singulier = "un SMS"
    objet_pluriel = "des SMS"
    boutons_liste = [
        {"label": "Créer un nouveau SMS", "classe": "btn btn-success", "href": reverse_lazy(url_modifier), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = SMS

    def get_queryset(self):
        return SMS.objects.select_related("utilisateur").filter(self.Get_filtres("Q")).annotate(nbre_destinataires=Count("destinataires"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        context['active_checkbox'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ['idsms', 'objet']
        check = columns.CheckBoxSelectColumn(label="")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        nbre_destinataires = columns.TextColumn("Destinataires", sources=['nbre_destinataires'])
        utilisateur = columns.TextColumn("Auteur", sources=None, processor='Formate_utilisateur')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', 'idsms', 'date_creation', 'objet', 'nbre_destinataires', "utilisateur"]
            ordering = ['date_creation']
            processors = {
                'date_creation': helpers.format_date('%d/%m/%Y %H:%M'),
            }

        def Formate_utilisateur(self, instance, **kwargs):
            if instance.utilisateur:
                return instance.utilisateur.get_full_name() or instance.utilisateur.get_short_name() or instance.utilisateur
            return ""


class Supprimer(Page, crud.Supprimer):
    pass


class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
    pass
