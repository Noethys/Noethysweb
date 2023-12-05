# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.urls import reverse
from django.db.models import Q, Sum, DecimalField, Case, When, F
from core.views.mydatatableview import MyDatatable, columns
from core.views import crud
from core.models import CompteBancaire
from core.utils import utils_texte


class Page(crud.Page):
    model = CompteBancaire
    menu_code = "comptabilite_liste_comptes"
    url_liste = "comptabilite_liste_comptes"
    objet_pluriel = "des comptes bancaires"


class Liste(Page, crud.Liste):
    model = CompteBancaire

    def get_queryset(self):
        return CompteBancaire.objects.filter(self.Get_filtres("Q"), self.Get_condition_structure()).annotate(
            solde_final=Sum(Case(When(comptaoperation__type="credit", then=F("comptaoperation__montant")), output_field=DecimalField(), default=0)) - Sum(Case(When(comptaoperation__type="debit", then=F("comptaoperation__montant")), output_field=DecimalField(), default=0)),
            solde_pointe=Sum(Case(When(comptaoperation__type="credit", comptaoperation__releve__isnull=False, then=F("comptaoperation__montant")), output_field=DecimalField(), default=0)) - Sum(Case(When(comptaoperation__type="debit", comptaoperation__releve__isnull=False, then=F("comptaoperation__montant")), output_field=DecimalField(), default=0)),
            solde_jour=Sum(Case(When(comptaoperation__type="credit", comptaoperation__date__lte=datetime.date.today(), then=F("comptaoperation__montant")), output_field=DecimalField(), default=0)) - Sum(Case(When(comptaoperation__type="debit", comptaoperation__date__lte=datetime.date.today(), then=F("comptaoperation__montant")), output_field=DecimalField(), default=0)),
        )

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Liste des comptes bancaires"
        context['box_titre'] = "Liste des comptes bancaires"
        context['box_introduction'] = "Voici ci-dessous la liste des comptes bancaires."
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ["idcompte", "numero", "nom"]
        solde_final = columns.TextColumn("Solde final", sources="solde_final", processor="Formate_montant")
        solde_pointe = columns.TextColumn("Solde pointé", sources="solde_pointe", processor="Formate_montant")
        solde_jour = columns.TextColumn("Solde du jour", sources="solde_jour", processor="Formate_montant")
        numero = columns.TextColumn("Numéro", sources=None, processor='Get_numero')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idcompte", "numero", "nom", "solde_jour", "solde_pointe", "solde_final", "actions"]
            ordering = ["nom"]

        def Get_numero(self, instance, **kwargs):
            return instance.numero

        def Formate_montant(self, instance, **kwargs):
            return utils_texte.Formate_montant(kwargs["default_value"])

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton(url=reverse("operations_tresorerie_liste", args=[instance.pk]), title="Accéder aux opérations du compte", icone="fa-search"),
            ]
            return self.Create_boutons_actions(html)
