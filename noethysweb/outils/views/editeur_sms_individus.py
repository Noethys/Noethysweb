# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from core.views import crud
from core.models import Individu, DestinataireSMS
from core.views.mydatatableview import MyDatatable, columns, helpers
from outils.views.editeur_sms import Page_destinataires


class Liste(Page_destinataires, crud.Liste):
    model = Individu
    template_name = "outils/editeur_sms_destinataires.html"
    categorie = "individu"

    def get_queryset(self):
        return Individu.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['box_titre'] = "Sélection d'individus"
        context['box_introduction'] = context['box_introduction'] = "Cochez les individus souhaités ci-dessous. Cochez la case de l'entête en haut à gauche pour cocher tous les individus affichés. Astuce : Utilisez le bouton Filtrer <i class='fa fa-filter text-gray'></i> pour sélectionner les inscrits d'une ou plusieurs activités données ou les présents d'une période spécifique."
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        context["hauteur_table"] = "400px"
        context['liste_coches'] = [destinataire.individu_id for destinataire in DestinataireSMS.objects.filter(categorie="individu", sms=self.kwargs.get("idsms"))]
        return context

    class datatable_class(MyDatatable):
        filtres = ["igenerique:pk", "idindividu"]
        check = columns.CheckBoxSelectColumn(label="")
        tel_mobile = columns.TextColumn("Tél portable", processor="Get_tel_mobile")
        mail = columns.TextColumn("Email", processor='Get_mail')
        rue_resid = columns.TextColumn("Rue", processor='Get_rue_resid')
        cp_resid = columns.TextColumn("CP", processor='Get_cp_resid')
        ville_resid = columns.TextColumn("Ville",  sources=None, processor='Get_ville_resid')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', "idindividu", "nom", "prenom", "tel_mobile", "rue_resid", "cp_resid", "ville_resid"]
            ordering = ["nom", "prenom"]

        def Get_tel_mobile(self, instance, *args, **kwargs):
            return instance.tel_mobile

        def Get_mail(self, instance, *args, **kwargs):
            return instance.mail

        def Get_rue_resid(self, instance, *args, **kwargs):
            return instance.rue_resid

        def Get_cp_resid(self, instance, *args, **kwargs):
            return instance.cp_resid

        def Get_ville_resid(self, instance, *args, **kwargs):
            return instance.ville_resid
