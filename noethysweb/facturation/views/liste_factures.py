# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Facture, Ventilation
from core.utils import utils_preferences
from decimal import Decimal
from django.db.models import Sum


class Page(crud.Page):
    model = Facture
    url_liste = "liste_factures"
    description_liste = "Voici ci-dessous la liste des factures."
    objet_singulier = "une facture"
    objet_pluriel = "des factures"
    url_supprimer_plusieurs = "factures_supprimer_plusieurs"


class Liste(Page, crud.Liste):
    model = Facture

    def get_queryset(self):
        return Facture.objects.select_related('famille', 'lot', 'prefixe', 'regie').filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['active_checkbox'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:famille", 'idfacture', 'date_edition', 'prefixe', 'numero', 'date_debut', 'date_fin', 'total', 'solde',
                   'solde_actuel', 'lot__nom', "regie__nom", "date_limite_paiement"]
        check = columns.CheckBoxSelectColumn(label="")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        solde_actuel = columns.TextColumn("Solde actuel", sources=['solde_actuel'], processor='Get_solde_actuel')
        lot = columns.TextColumn("Lot", sources=['lot__nom'])
        numero = columns.CompoundColumn("Numéro", sources=['prefixe__prefixe', 'numero'])
        regie = columns.TextColumn("Régie", sources=['regie__nom'])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', 'idfacture', 'date_edition', 'numero', 'date_debut', 'date_fin', 'famille', 'total', 'solde', 'solde_actuel', 'lot', 'regie', "date_limite_paiement"]
            processors = {
                'date_edition': helpers.format_date('%d/%m/%Y'),
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
                'date_echeance': helpers.format_date('%d/%m/%Y'),
                'date_limite_paiement': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ["date_edition"]
            hidden_columns = ["regie", "date_limite_paiement"]

        def Get_solde_actuel(self, instance, **kwargs):
            if instance.etat == "annulation":
                return "<span class='text-red'><i class='fa fa-trash'></i> Annulée</span>"
            icone = "fa-check text-green" if instance.solde_actuel == 0 else "fa-close text-red"
            return "<i class='fa %s margin-r-5'></i>  %0.2f %s" % (icone, instance.solde_actuel, utils_preferences.Get_symbole_monnaie())

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_modifier(url=reverse("famille_factures_modifier", kwargs={"idfamille": instance.famille_id, "pk": instance.pk})),
                self.Create_bouton_imprimer(url=reverse("famille_voir_facture", kwargs={"idfamille": instance.famille_id, "idfacture": instance.pk}), title="Imprimer ou envoyer par email la facture"),
            ]
            return self.Create_boutons_actions(html)


class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
    pass
