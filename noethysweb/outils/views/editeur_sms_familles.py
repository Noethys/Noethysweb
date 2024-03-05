# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from core.views import crud
from core.models import Famille, DestinataireSMS
from core.views.mydatatableview import MyDatatable, columns, helpers
from outils.views.editeur_sms import Page_destinataires


class Liste(Page_destinataires, crud.Liste):
    model = Famille
    template_name = "outils/editeur_sms_destinataires.html"
    categorie = "famille"

    def get_queryset(self):
        return Famille.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['box_titre'] = "Sélection de familles"
        context['box_introduction'] = "Cochez les familles souhaitées ci-dessous. Cochez la case de l'entête en haut à gauche pour cocher toutes les familles affichées. Astuce : Utilisez le bouton Filtrer <i class='fa fa-filter text-gray'></i> pour sélectionner les inscrits d'une ou plusieurs activités données ou les présents d'une période spécifique."
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        context["hauteur_table"] = "400px"
        context['liste_coches'] = [destinataire.famille_id for destinataire in DestinataireSMS.objects.filter(categorie="famille", sms=self.kwargs.get("idsms"))]
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:pk", "idfamille", "caisse__nom"]
        check = columns.CheckBoxSelectColumn(label="")
        mobile = columns.TextColumn("Portable", processor='Get_mobile')
        rue_resid = columns.TextColumn("Rue", processor='Get_rue_resid')
        cp_resid = columns.TextColumn("CP", processor='Get_cp_resid')
        ville_resid = columns.TextColumn("Ville",  sources=None, processor='Get_ville_resid')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', "idfamille", "nom", "mobile", "rue_resid", "cp_resid", "ville_resid"]
            ordering = ["nom"]

        def Get_mobile(self, instance, *args, **kwargs):
            if instance.mobile_blocage:
                return "<span class='text-red' title='La famille ne souhaite pas recevoir des SMS groupés'><i class='fa fa-ban'></i> %s</span>" % instance.mobile
            return instance.mobile

        def Get_rue_resid(self, instance, *args, **kwargs):
            return instance.rue_resid

        def Get_cp_resid(self, instance, *args, **kwargs):
            return instance.cp_resid

        def Get_ville_resid(self, instance, *args, **kwargs):
            return instance.ville_resid
