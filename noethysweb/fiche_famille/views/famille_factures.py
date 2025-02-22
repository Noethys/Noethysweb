# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.db.models import Q
from django.urls import reverse_lazy, reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Facture, Prestation
from core.utils import utils_preferences
from fiche_famille.forms.famille_factures import Formulaire, Formulaire_annulation
from fiche_famille.views.famille import Onglet


class Page(Onglet):
    model = Facture
    url_liste = "famille_factures_liste"
    url_supprimer = "famille_factures_supprimer"
    url_supprimer_plusieurs = "famille_factures_supprimer_plusieurs"
    description_liste = "Vous pouvez consulter ici les factures de la famille. Les boutons d'action vous permettent de modifier le contenu d'une facture, de la supprimer ou de la visualiser au format PDF ou de l'envoyer par email."
    description_saisie = "Saisissez toutes les informations concernant la facture et cliquez sur le bouton Enregistrer."
    objet_singulier = "une facture"
    objet_pluriel = "des factures"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Factures"
        context['onglet_actif'] = "factures"
        if self.request.user.has_perm("core.famille_factures_modifier"):
            context['boutons_liste'] = [
                {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy("factures_generation", kwargs={'idfamille': self.kwargs.get('idfamille', None)}), "icone": "fa fa-plus"},
            ]
        context['bouton_supprimer'] = self.request.user.has_perm("core.famille_factures_modifier")
        context['url_supprimer_plusieurs'] = reverse_lazy(self.url_supprimer_plusieurs, kwargs={'idfamille': self.kwargs.get('idfamille', None), "listepk": "xxx"})
        return context

    def test_func_page(self):
        if getattr(self, "verbe_action", None) in ("Ajouter", "Modifier", "Supprimer", "Annuler") and not self.request.user.has_perm("core.famille_factures_modifier"):
            return False
        return True

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idindividu au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idfamille"] = self.Get_idfamille()
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idfamille': self.kwargs.get('idfamille', None)})


class Liste(Page, crud.Liste):
    model = Facture
    template_name = "fiche_famille/famille_factures.html"

    def get_queryset(self):
        return Facture.objects.select_related('lot', 'prefixe').filter(Q(famille__pk=self.Get_idfamille()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['active_checkbox'] = True
        context['boutons_coches'] = json.dumps([
            {"id": "bouton_tout_annuler", "action": "tout_annuler()", "title": "Annuler les factures cochées", "label": "<i class='fa fa-times margin-r-5'></i>Annuler"},
        ])
        return context

    class datatable_class(MyDatatable):
        filtres = ['idfacture', 'date_edition', 'prefixe', 'numero', 'date_debut', 'date_fin', 'total', 'solde', 'solde_actuel', 'lot__nom', 'observations']
        check = columns.CheckBoxSelectColumn(label="")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        solde_actuel = columns.TextColumn("Solde actuel", sources=['solde_actuel'], processor='Get_solde_actuel')
        lot = columns.TextColumn("Lot", sources=['lot__nom'])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', 'idfacture', 'date_edition', 'prefixe', 'numero', 'date_debut', 'date_fin', 'total', 'solde', 'solde_actuel', 'lot', 'observations']
            hidden_columns = ["observations"]
            processors = {
                'date_edition': helpers.format_date('%d/%m/%Y'),
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
                'date_echeance': helpers.format_date('%d/%m/%Y'),
                'total': "Formate_montant_standard",
                'solde': "Formate_montant_standard",
            }
            ordering = ['date_debut']

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idindividu dans les boutons d'actions """
            view = kwargs["view"]
            if not view.request.user.has_perm("core.famille_factures_modifier"):
                return "<span class='text-red' title='Accès interdit'><i class='fa fa-lock'></i></span>"
            kwargs = view.kwargs
            kwargs["pk"] = instance.pk
            html = [
                self.Create_bouton(url=reverse("famille_factures_consulter", kwargs={"idfamille": kwargs["idfamille"], "pk": instance.pk}), title="Consulter", icone="fa-search"),
                """<a type='button' class='btn btn-default btn-xs' href='#' onclick="ouvrir_modal_supprimer_facture(%d);" title='Supprimer ou annuler'><i class="fa fa-fw fa-times"></i></a>""" % instance.pk,
                self.Create_bouton_imprimer(url=reverse("famille_voir_facture", kwargs={"idfamille": kwargs["idfamille"], "idfacture": instance.pk}), title="Imprimer ou envoyer par email la facture"),
            ]
            return self.Create_boutons_actions(html)

        def Get_solde_actuel(self, instance, **kwargs):
            if instance.etat == "annulation":
                return "<span class='text-red'><i class='fa fa-trash'></i> Annulée</span>"
            icone = "fa-check text-green" if instance.solde_actuel == 0 else "fa-close text-red"
            return "<i class='fa %s margin-r-5'></i>  %0.2f %s" % (icone, instance.solde_actuel, utils_preferences.Get_symbole_monnaie())


class ClasseCommune(Page):
    form_class = Formulaire
    template_name = "fiche_famille/famille_factures.html"

    def get_context_data(self, *args, **kwargs):
        context_data = super(ClasseCommune, self).get_context_data(**kwargs)
        return context_data


class Ajouter(ClasseCommune, crud.Ajouter):
    form_class = Formulaire
    template_name = "fiche_famille/famille_edit.html"


class Supprimer(Page, crud.Supprimer):
    template_name = "fiche_famille/famille_delete.html"


class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
    template_name = "fiche_famille/famille_delete.html"


class Annuler(Page, crud.Supprimer):
    template_name = "fiche_famille/famille_delete.html"
    verbe_action = "Annuler"
    nom_action = "Annulation"

    def get_context_data(self, **kwargs):
        """ Ajout d'un formulaire à la page d'annulation """
        context = super(Annuler, self).get_context_data(**kwargs)
        context["form"] = Formulaire_annulation()
        return context

    def delete(self, request, *args, **kwargs):
        # Importation du formulaire du commentaire
        form = Formulaire_annulation(request.POST, request=request)
        form.is_valid()

        # Annulation de la facture
        facture = Facture.objects.get(pk=kwargs["pk"])
        if form.cleaned_data.get("observations", None):
            facture.observations = form.cleaned_data["observations"]
        facture.etat = "annulation"
        facture.save()
        Prestation.objects.filter(facture=facture).update(facture=None)

        # Confirmation de la suppression
        messages.add_message(self.request, messages.SUCCESS, "La facture a été annulée avec succès")
        return HttpResponseRedirect(reverse_lazy(self.url_liste, kwargs={"idfamille": kwargs["idfamille"]}))


class Annuler_plusieurs(Page, crud.Supprimer_plusieurs):
    template_name = "fiche_famille/famille_delete.html"
    verbe_action = "Annuler"
    nom_action = "Annulation"

    def get_context_data(self, **kwargs):
        """ Ajout d'un formulaire à la page d'annulation """
        context = super(Annuler_plusieurs, self).get_context_data(**kwargs)
        context["form"] = Formulaire_annulation()
        return context

    def post(self, request, **kwargs):
        # Importation du formulaire du commentaire
        form = Formulaire_annulation(request.POST, request=request)
        form.is_valid()

        # Annulation des factures
        for facture in self.get_objets():
            if form.cleaned_data.get("observations", None):
                facture.observations = form.cleaned_data["observations"]
            facture.etat = "annulation"
            facture.save()
            Prestation.objects.filter(facture=facture).update(facture=None)

        # Confirmation de la suppression
        messages.add_message(self.request, messages.SUCCESS, "Les factures ont été annulées avec succès")
        return HttpResponseRedirect(reverse_lazy(self.url_liste, kwargs={"idfamille": kwargs["idfamille"]}))
