# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views import crud
from core.models import Famille, Destinataire, Mail
from core.views.mydatatableview import MyDatatable, columns, helpers
from outils.views.editeur_emails import Page_destinataires



class Liste(Page_destinataires, crud.Liste):
    model = Famille
    template_name = "outils/editeur_emails_destinataires.html"
    categorie = "famille"

    def get_queryset(self):
        return Famille.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['box_titre'] = "Sélection de familles"
        context['box_introduction'] = "Sélectionnez des familles ci-dessous."
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        context["hauteur_table"] = "400px"
        context['liste_coches'] = [destinataire.famille_id for destinataire in Destinataire.objects.filter(categorie="famille", mail=self.kwargs.get("idmail"))]
        return context

    class datatable_class(MyDatatable):
        filtres = ["fpresent:pk", "idfamille", "nom", "rue_resid", "cp_resid", "ville_resid", "mail"]
        check = columns.CheckBoxSelectColumn(label="")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', "idfamille", "nom", "mail", "rue_resid", "cp_resid", "ville_resid"]
            ordering = ["nom"]
