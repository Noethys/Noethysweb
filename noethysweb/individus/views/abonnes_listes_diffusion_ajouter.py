# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from core.views import crud
from core.models import Individu, ListeDiffusion
from core.views.mydatatableview import MyDatatable, columns


class Liste(crud.Page, crud.Liste):
    model = Individu
    template_name = "individus/abonnes_listes_diffusion_ajouter.html"

    def get_queryset(self):
        return Individu.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['box_titre'] = "Sélection d'individus"
        context['box_introduction'] = context['box_introduction'] = "Cochez ci-dessous les individus à abonner. Cochez la case de l'entête en haut à gauche pour cocher tous les individus affichés. Astuce : Utilisez le bouton Filtrer <i class='fa fa-filter text-gray'></i> pour sélectionner les inscrits d'une ou plusieurs activités données ou les présents d'une période spécifique."
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        context["hauteur_table"] = "400px"
        context["idliste_diffusion"] = self.kwargs.get("idliste_diffusion")
        return context

    def post(self, request, **kwargs):
        liste_diffusion = ListeDiffusion.objects.get(pk=self.kwargs.get("idliste_diffusion"))
        for individu in Individu.objects.filter(pk__in=json.loads(request.POST.get("selections"))):
            if liste_diffusion not in individu.listes_diffusion.all():
                individu.listes_diffusion.add(liste_diffusion)
        return HttpResponseRedirect(reverse_lazy("abonnes_listes_diffusion_liste", kwargs={"categorie": self.kwargs.get("idliste_diffusion")}))

    class datatable_class(MyDatatable):
        filtres = ["igenerique:pk",]
        check = columns.CheckBoxSelectColumn(label="")
        mail = columns.TextColumn("Email", processor='Get_mail')
        rue_resid = columns.TextColumn("Rue", processor='Get_rue_resid')
        cp_resid = columns.TextColumn("CP", processor='Get_cp_resid')
        ville_resid = columns.TextColumn("Ville",  sources=None, processor='Get_ville_resid')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', "idindividu", "nom", "prenom", "mail", "rue_resid", "cp_resid", "ville_resid"]
            ordering = ["nom", "prenom"]

        def Get_mail(self, instance, *args, **kwargs):
            return instance.mail

        def Get_rue_resid(self, instance, *args, **kwargs):
            return instance.rue_resid

        def Get_cp_resid(self, instance, *args, **kwargs):
            return instance.cp_resid

        def Get_ville_resid(self, instance, *args, **kwargs):
            return instance.ville_resid
