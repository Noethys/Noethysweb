# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from core.views import crud
from core.models import Collaborateur, Destinataire
from core.views.mydatatableview import MyDatatable, columns
from outils.views.editeur_emails import Page_destinataires


class Liste(Page_destinataires, crud.Liste):
    model = Collaborateur
    template_name = "outils/editeur_emails_destinataires.html"
    categorie = "collaborateur"

    def get_queryset(self):
        return Collaborateur.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['box_titre'] = "Sélection de collaborateurs"
        context['box_introduction'] = context['box_introduction'] = "Cochez les collaborateurs souhaités ci-dessous. Cochez la case de l'entête en haut à gauche pour cocher tous les collaborateurs affichés. Astuce : Utilisez le bouton Filtrer <i class='fa fa-filter text-gray'></i> pour sélectionner les présents d'une période spécifique."
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        context["hauteur_table"] = "400px"
        context['liste_coches'] = [destinataire.collaborateur_id for destinataire in Destinataire.objects.filter(categorie="collaborateur", mail=self.kwargs.get("idmail"))]
        return context

    class datatable_class(MyDatatable):
        filtres = ["idcollaborateur", "nom", "prenom", "mail", "rue_resid", "cp_resid", "ville_resid"]
        check = columns.CheckBoxSelectColumn(label="")
        mail = columns.TextColumn("Email", processor="Get_mail")
        rue_resid = columns.TextColumn("Rue", processor='Get_rue_resid')
        cp_resid = columns.TextColumn("CP", processor='Get_cp_resid')
        ville_resid = columns.TextColumn("Ville",  sources=None, processor='Get_ville_resid')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', "idcollaborateur", "nom", "prenom", "mail", "rue_resid", "cp_resid", "ville_resid"]
            ordering = ["nom", "prenom"]

        def Get_mail(self, instance, *args, **kwargs):
            return instance.mail

        def Get_rue_resid(self, instance, *args, **kwargs):
            return instance.rue_resid

        def Get_cp_resid(self, instance, *args, **kwargs):
            return instance.cp_resid

        def Get_ville_resid(self, instance, *args, **kwargs):
            return instance.ville_resid
