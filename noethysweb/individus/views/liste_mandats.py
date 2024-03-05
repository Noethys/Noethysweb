# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.http import HttpResponseRedirect
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Mandat
from fiche_famille.forms.famille_mandat import Formulaire, Formulaire_creation


class Page(crud.Page):
    model = Mandat
    url_liste = "mandats_liste"
    url_ajouter = "mandats_creer"
    url_modifier = "mandats_modifier"
    url_supprimer = "mandats_supprimer"
    description_liste = "Voici ci-dessous la liste des mandats SEPA des familles."
    description_saisie = "Saisissez toutes les informations concernant le mandat à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un mandat"
    objet_pluriel = "des mandats"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = Mandat

    def get_queryset(self):
        return Mandat.objects.select_related("famille").filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['page_titre'] = "Mandats SEPA des familles"
        context['box_titre'] = "Liste des mandats SEPA"
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:famille", "idmandat", "date", "rum", "actif", "sequence"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        iban = columns.TextColumn("IBAN", sources=[], processor='Get_iban')
        bic = columns.TextColumn("BIC", sources=[], processor='Get_bic')
        actif = columns.TextColumn("Etat", sources=["actif"], processor='Get_actif')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idmandat", "famille", "date", "rum", "iban", "bic", "actif", "sequence"]
            ordering = ["date"]
            hidden_columns = ["sequence"]
            processors = {
                'date': helpers.format_date('%d/%m/%Y'),
            }

        def Get_actif(self, instance, *args, **kwargs):
            return "<small class='badge badge-success'>Activé</small>" if instance.actif else "<small class='badge badge-danger'>Désactivé</small>"

        def Get_iban(self, instance, *args, **kwargs):
            return instance.iban[:-5] + "*****"

        def Get_bic(self, instance, *args, **kwargs):
            return instance.bic[:-5] + "*****"

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.pk])),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.pk])),
                self.Create_bouton(url=reverse("famille_resume", args=[instance.famille_id]), title="Ouvrir la fiche famille", icone="fa-users"),
            ]
            return self.Create_boutons_actions(html)


class Creer(Page, crud.Ajouter):
    form_class = Formulaire_creation
    template_name = "core/crud/edit.html"

    def get_context_data(self, **kwargs):
        context = super(Creer, self).get_context_data(**kwargs)
        context['box_introduction'] = "Vous devez sélectionner la famille associée au mandat."
        return context

    def post(self, request, **kwargs):
        idfamille = request.POST.get("famille")
        return HttpResponseRedirect(reverse_lazy("mandats_ajouter", kwargs={"idfamille": idfamille}))

class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idfamille"] = self.kwargs.get("idfamille", 0)
        return form_kwargs

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    form_class = Formulaire
