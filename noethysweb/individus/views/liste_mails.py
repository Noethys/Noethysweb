# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from core.views.mydatatableview import MyDatatable, columns
from core.views import crud
from core.models import Rattachement


class Page(crud.Page):
    model = Rattachement
    url_liste = "mails_liste"
    description_liste = "Voici ci-dessous la liste des adresses Emails associées à chaque individu. Si l'individu ne possède pas d'adresse, c'est l'adresse favorite de la famille rattachée qui est affichée."
    objet_singulier = "une adresse Email"
    objet_pluriel = "des adresses Emails"


class Liste(Page, crud.Liste):
    model = Rattachement

    def get_queryset(self):
        return Rattachement.objects.select_related("individu", "famille").filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Emails"
        context['box_titre'] = "Liste des Emails"
        return context

    class datatable_class(MyDatatable):
        filtres = ["idrattachement", "igenerique:individu", "fgenerique:famille"]
        nom = columns.TextColumn("Nom", sources=['individu__nom'])
        prenom = columns.TextColumn("Prénom", sources=['individu__prenom'])
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        profil = columns.TextColumn("Profil", sources=['Get_profil'])
        mail = columns.TextColumn("Email associé", processor="Get_mail")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idrattachement", "nom", "prenom", "profil", "famille", "mail"]
            ordering = ["individu__nom", "individu__prenom"]

        def Get_mail(self, instance, *args, **kwargs):
            if instance.individu.mail:
                return instance.individu.mail
            return instance.famille.mail
