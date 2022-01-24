# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views import crud
from core.models import Individu, Destinataire, Mail
from core.views.mydatatableview import MyDatatable, columns, helpers
from outils.views.editeur_emails import Page_destinataires



class Liste(Page_destinataires, crud.Liste):
    model = Individu
    template_name = "outils/editeur_emails_destinataires.html"
    categorie = "individu"

    def get_queryset(self):
        return Individu.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['box_titre'] = "Sélection d'individus"
        context['box_introduction'] = "Sélectionnez des individus ci-dessous."
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        context["hauteur_table"] = "400px"
        context['liste_coches'] = [destinataire.individu_id for destinataire in Destinataire.objects.filter(categorie="individu", mail=self.kwargs.get("idmail"))]
        return context

    class datatable_class(MyDatatable):
        filtres = ["ipresent:pk", "iscolarise:pk", "idindividu", "nom", "prenom", "mail", "rue_resid", "cp_resid", "ville_resid"]
        check = columns.CheckBoxSelectColumn(label="")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', "idindividu", "nom", "prenom", "mail", "rue_resid", "cp_resid", "ville_resid"]
            ordering = ["nom", "prenom"]

