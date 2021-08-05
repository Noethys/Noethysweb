# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Facture, Ventilation
from fiche_famille.forms.famille_factures import Formulaire
from fiche_famille.views.famille import Onglet
from django.db.models import Sum, Q
from core.utils import utils_preferences
from decimal import Decimal


class Page(Onglet):
    model = Facture
    url_liste = "famille_factures_liste"
    url_modifier = "famille_factures_modifier"
    url_supprimer = "famille_factures_supprimer"
    description_liste = "Saisissez ici les factures de la famille."
    description_saisie = "Saisissez toutes les informations concernant la facture et cliquez sur le bouton Enregistrer."
    objet_singulier = "une facture"
    objet_pluriel = "des factures"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Factures"
        context['onglet_actif'] = "factures"
        context['boutons_liste'] = [
            {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy("factures_generation", kwargs={'idfamille': self.kwargs.get('idfamille', None)}), "icone": "fa fa-plus"},
        ]
        return context

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
        return context

    class datatable_class(MyDatatable):
        filtres = ['idfacture', 'date_edition', 'prefixe', 'numero', 'date_debut', 'date_fin', 'total', 'solde', 'solde_actuel', 'lot__nom']

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        solde_actuel = columns.TextColumn("Solde actuel", sources=['solde_actuel'], processor='Get_solde_actuel')
        lot = columns.TextColumn("Lot", sources=['lot__nom'])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idfacture', 'date_edition', 'prefixe', 'numero', 'date_debut', 'date_fin', 'total', 'solde', 'solde_actuel', 'lot']
            #hidden_columns = = ["idfacture"]
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
            # Récupération idfamille
            kwargs = view.kwargs

            # Ajoute l'id de la ligne
            kwargs["pk"] = instance.pk
            html = [
                self.Create_bouton_modifier(url=reverse(view.url_modifier, kwargs=kwargs)),
                self.Create_bouton_supprimer(url=reverse(view.url_supprimer, kwargs=kwargs)),
                self.Create_bouton_imprimer(url=reverse("famille_voir_facture", kwargs={"idfamille": kwargs["idfamille"], "idfacture": instance.pk}), title="Imprimer ou envoyer par email la facture"),
            ]
            return self.Create_boutons_actions(html)

        def Get_solde_actuel(self, instance, **kwargs):
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


class Modifier(ClasseCommune, crud.Modifier):
    form_class = Formulaire
    template_name = "fiche_famille/famille_edit.html"


class Supprimer(Page, crud.Supprimer):
    template_name = "fiche_famille/famille_delete.html"
