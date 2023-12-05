# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import PortailMessage
from django.template.defaultfilters import truncatechars, striptags


class Page(crud.Page):
    model = PortailMessage
    url_liste = "messages_portail_liste"
    url_supprimer = "messages_portail_supprimer"
    description_liste = "Voici ci-dessous la liste des messages du portail."
    objet_singulier = "un message"
    objet_pluriel = "des messages"


class Liste(Page, crud.Liste):
    model = PortailMessage
    template_name = "outils/messages_portail.html"

    def get_queryset(self):
        return PortailMessage.objects.select_related("famille", "structure", "utilisateur").filter(structure__in=self.request.user.structures.all())

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        context['active_checkbox'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ['idmessage', 'famille__nom', 'structure__nom', 'date_creation', 'date_lecture']
        check = columns.CheckBoxSelectColumn(label="")
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        structure = columns.TextColumn("Structure", sources=['structure__nom'])
        texte = columns.TextColumn("Texte", sources=["texte"], processor='Get_texte')
        date_lecture = columns.TextColumn("Lu", sources=["date_lecture"], processor='Get_date_lecture')
        auteur = columns.TextColumn("Auteur", sources=None, processor='Get_auteur')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', 'idmessage', 'date_creation', 'famille', 'structure', 'texte', 'auteur', 'date_lecture']
            ordering = ['date_creation']
            labels = {
                'date_creation': "date"
            }
            processors = {
                'date_creation': helpers.format_date('%d/%m/%Y %H:%M'),
            }

        def Get_date_lecture(self, instance, *args, **kwargs):
            if instance.date_lecture:
                return instance.date_lecture.strftime('%d/%m/%Y %H:%m')
            return "<span class='badge bg-danger'>Non lu</span>"

        def Get_texte(self, instance, *args, **kwargs):
            return truncatechars(striptags(instance.texte), 50)

        def Get_auteur(self, instance, *args, **kwargs):
            if instance.utilisateur:
                return instance.utilisateur
            return instance.famille.nom

        def Get_actions(self, instance, *args, **kwargs):
            view = kwargs["view"]
            kwargs = view.kwargs
            kwargs["pk"] = instance.pk
            html = []
            if not instance.date_lecture:
                html.append("""<button class='btn btn-success btn-xs' onclick="marquer_lu(%d, 'true')" title='Marquer comme lu'><i class="fa fa-fw fa-eye"></i></button>""" % instance.pk)
            else:
                html.append("""<button class='btn btn-danger btn-xs' onclick="marquer_lu(%d, 'false')" title='Marquer comme non lu'><i class="fa fa-fw fa-eye-slash"></i></button>""" % instance.pk)
            html.append("""<a class='btn btn-default btn-xs' href="%s" title="Accéder à la discussion"><i class="fa fa-fw fa-comments"></i></button>""" % reverse_lazy("famille_messagerie_portail", kwargs={'idstructure': instance.structure_id, 'idfamille': instance.famille_id}))
            html.append(self.Create_bouton_supprimer(url=reverse(view.url_supprimer, kwargs=kwargs)),)
            return self.Create_boutons_actions(html)


class Supprimer(Page, crud.Supprimer):
    pass
