# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Deduction
from django.urls import reverse
from core.utils import utils_dates


class Page(crud.Page):
    model = Deduction
    url_liste = "prestations_liste"
    description_liste = "Voici ci-dessous la liste des déductions."
    objet_singulier = "une déduction"
    objet_pluriel = "des déductions"


class Liste(Page, crud.Liste):
    model = Deduction

    def get_queryset(self):
        #Filtrage en fonction des autorisations
        activites_autorisees = self.request.user.structures.all()
        return Deduction.objects.select_related('prestation', 'prestation__activite', 'prestation__facture', 'prestation__individu').filter(self.Get_filtres("Q"),prestation__activite__structure__in=activites_autorisees)
        return Prestation.objects.select_related('activite', 'famille', 'individu', 'tarif', 'facture').filter(self.Get_filtres("Q"), activite__structure__in=activites_autorisees)

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ["ipresent:prestation__individu", "fpresent:famille", "iscolarise:prestation__individu", "fscolarise:famille", "iddeduction", "date", "label",
                   "famille__nom", "individu__nom", "montant", "prestation__code_compta"]
        activite = columns.TextColumn("Activité", sources=['prestation__activite__nom'])
        individu = columns.CompoundColumn("Individu", sources=['prestation__individu__nom', 'prestation__individu__prenom'])
        date_naiss = columns.TextColumn("Date naiss.", processor="Get_date_naiss")
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        num_facture = columns.CompoundColumn("N° Facture", sources=['prestation__facture__numero'])
        code_compta_prestation = columns.CompoundColumn("Code compta presta.", sources=['prestation__code_compta'])
        caisse = columns.TextColumn("Caisse", sources=["aide__caisse__nom"])
        allocataire = columns.TextColumn("Allocataire titulaire", sources=['allocataire__nom', 'allocataire__prenom'])
        num_allocataire = columns.TextColumn("N° Allocataire", sources=None, processor='Get_num_allocataire')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["iddeduction", "date", "label", "famille", "individu", "date_naiss", "montant", "activite", "num_facture", "code_compta_prestation", "num_allocataire", "allocataire", "caisse"]
            hidden_columns = []
            processors = {
                'date': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ["date"]
            
        def Get_date_naiss(self, instance, *args, **kwargs):
            return utils_dates.ConvertDateToFR(instance.prestation.individu.date_naiss) if instance.prestation.individu else ""

        def Get_num_allocataire(self, instance, *args, **kwargs):
            return instance.famille.num_allocataire
            
        #Bouton modification de la prestation
        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_modifier(url=reverse("famille_prestations_modifier", kwargs={"idfamille": instance.famille_id, "pk": instance.prestation.idprestation})),
                ]

            return self.Create_boutons_actions(html)