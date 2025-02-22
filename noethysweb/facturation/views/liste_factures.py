# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.http import HttpResponseRedirect
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Facture, Prestation
from core.utils import utils_preferences
from fiche_famille.forms.famille_factures import Formulaire_annulation


class Page(crud.Page):
    model = Facture
    url_liste = "liste_factures"
    description_liste = "Voici ci-dessous la liste des factures. Les boutons d'action vous permettent de modifier le contenu d'une facture, de la supprimer ou de la visualiser au format PDF ou de l'envoyer par email."
    objet_singulier = "une facture"
    objet_pluriel = "des factures"
    url_supprimer = "listefactures_supprimer"
    url_supprimer_plusieurs = "liste_factures_supprimer_plusieurs"


class Liste(Page, crud.Liste):
    template_name = "facturation/liste_factures.html"
    model = Facture

    def get_queryset(self):
        return Facture.objects.select_related('famille', 'lot', 'prefixe', 'regie').filter(self.Get_filtres("Q"))

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
        filtres = ["fgenerique:famille", 'idfacture', 'date_edition', 'prefixe', 'numero', 'date_debut', 'date_fin', 'total', 'solde',
                   'solde_actuel', 'lot__nom', "regie__nom", "date_limite_paiement", "observations"]
        check = columns.CheckBoxSelectColumn(label="")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        solde_actuel = columns.TextColumn("Solde actuel", sources=['solde_actuel'], processor='Get_solde_actuel')
        lot = columns.TextColumn("Lot", sources=['lot__nom'])
        numero = columns.CompoundColumn("Numéro", sources=['prefixe__prefixe', 'numero'])
        regie = columns.TextColumn("Régie", sources=['regie__nom'])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', 'idfacture', 'date_edition', 'numero', 'date_debut', 'date_fin', 'famille', 'total', 'solde', 'solde_actuel', 'lot', 'regie', "date_limite_paiement", "observations"]
            processors = {
                'date_edition': helpers.format_date('%d/%m/%Y'),
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
                'date_echeance': helpers.format_date('%d/%m/%Y'),
                'date_limite_paiement': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ["date_edition"]
            hidden_columns = ["regie", "date_limite_paiement", "observations"]

        def Get_solde_actuel(self, instance, **kwargs):
            if instance.etat == "annulation":
                return "<span class='text-red'><i class='fa fa-trash'></i> Annulée</span>"
            icone = "fa-check text-green" if instance.solde_actuel == 0 else "fa-close text-red"
            return "<i class='fa %s margin-r-5'></i>  %0.2f %s" % (icone, instance.solde_actuel, utils_preferences.Get_symbole_monnaie())

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton(url=reverse("famille_factures_consulter", kwargs={"idfamille": instance.famille_id, "pk": instance.pk}), title="Consulter", icone="fa-search"),
                """<a type='button' class='btn btn-default btn-xs' href='#' onclick="ouvrir_modal_supprimer_facture(%d);" title='Supprimer ou annuler'><i class="fa fa-fw fa-times"></i></a>""" % instance.pk,
                self.Create_bouton_imprimer(url=reverse("famille_voir_facture", kwargs={"idfamille": instance.famille_id, "idfacture": instance.pk}), title="Imprimer ou envoyer par email la facture"),
            ]
            return self.Create_boutons_actions(html)


class Supprimer(Page, crud.Supprimer):
    pass


class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
    pass


class Annuler(Page, crud.Supprimer):
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
        return HttpResponseRedirect(reverse_lazy(self.url_liste))


class Annuler_plusieurs(Page, crud.Supprimer_plusieurs):
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
        return HttpResponseRedirect(reverse_lazy(self.url_liste))
