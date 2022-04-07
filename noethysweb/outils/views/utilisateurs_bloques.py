# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from axes.models import AccessAttempt


class Page(crud.Page):
    model = AccessAttempt
    url_liste = "utilisateurs_bloques_liste"
    url_supprimer = "utilisateurs_bloques_supprimer"
    description_liste = "Voici ci-dessous la liste des utilisateurs bloqués par le système de sécurité de Noethysweb. Le blocage intervient après un trop grand nombre de tentatives de connexion échouées au portail ou à l'administration. Supprimez une ligne pour débloquer l'utilisateur."
    objet_singulier = "un utilisateur bloqué"
    objet_pluriel = "des utilisateurs bloqués"


class Liste(Page, crud.Liste):
    model = AccessAttempt

    def get_queryset(self):
        return AccessAttempt.objects.all()

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        context['active_checkbox'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = []
        check = columns.CheckBoxSelectColumn(label="")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "id", "username", "ip_address", "attempt_time", "failures_since_start", "actions"]
            ordering = ['id']
            labels = {
                "username": "Identifiant",
                "ip_address": "Adresse IP",
                "attempt_time": "Date",
                "failures_since_start": "Tentatives",
            }
            processors = {
                "attempt_time": helpers.format_date('%d/%m/%Y %H:%M'),
            }

        def Get_actions(self, instance, *args, **kwargs):
            view = kwargs["view"]
            kwargs = view.kwargs
            kwargs["pk"] = instance.pk
            html = [
                self.Create_bouton_supprimer(url=reverse(view.url_supprimer, kwargs=kwargs))
            ]
            return self.Create_boutons_actions(html)


class Supprimer(Page, crud.Supprimer):
    pass
