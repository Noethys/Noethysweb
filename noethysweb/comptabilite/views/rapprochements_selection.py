# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import ComptaReleve, ComptaOperation


class Liste(crud.Page, crud.Liste):
    template_name = "comptabilite/rapprochements_selection.html"
    menu_code = "rapprochements_liste"
    model = ComptaOperation
    objet_pluriel = "des opérations"

    def get_queryset(self):
        return ComptaOperation.objects.select_related("tiers", "mode").filter(self.Get_filtres("Q"), releve_id__isnull=True)

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Rapprochement bancaire"
        context['box_titre'] = "Sélection des opérations"
        context['box_introduction'] = "Cochez les opérations à inclure dans le relevé et cliquez sur le bouton Ajouter."
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        context["hauteur_table"] = "400px"
        context['idreleve'] = self.kwargs.get("idreleve")
        return context

    class datatable_class(MyDatatable):
        filtres = ["idoperation", "type", "date", "libelle", "mode", "releve", "num_piece", "debit", "credit", "montant"]
        check = columns.CheckBoxSelectColumn(label="")
        tiers = columns.TextColumn("Tiers", sources=["tiers__nom"])
        debit = columns.TextColumn("Débit", sources=["montant"], processor="Get_montant_debit")
        credit = columns.TextColumn("Crédit", sources=["montant"], processor="Get_montant_credit")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idoperation", "date", "libelle", "tiers", "mode", "num_piece", "releve", "debit", "credit"]
            ordering = ["date"]
            processors = {
                "date": helpers.format_date('%d/%m/%Y'),
            }
            labels = {
                "mode": "Mode",
                "num_piece": "N° Pièce",
                "releve": "Relevé",
            }

        def Get_montant_debit(self, instance, **kwargs):
            if instance.type == "debit":
                return "%0.2f" % instance.montant
            return None

        def Get_montant_credit(self, instance, **kwargs):
            if instance.type == "credit":
                return "%0.2f" % instance.montant
            return None

    def post(self, request, **kwargs):
        idreleve = self.kwargs.get("idreleve")
        liste_selections = json.loads(request.POST.get("selections"))
        Enregistrement_operations(idreleve=idreleve, liste_idoperation=liste_selections)
        return HttpResponseRedirect(reverse_lazy("rapprochements_consulter", kwargs={'pk': idreleve}))


def Enregistrement_operations(idreleve=None, liste_idoperation=[]):
    # Importation des données
    releve = ComptaReleve.objects.get(pk=idreleve)
    nouvelles_operations = ComptaOperation.objects.filter(pk__in=liste_idoperation)

    # Modification de l'opération
    liste_modifications = []
    for operation in nouvelles_operations:
        operation.releve = releve
        liste_modifications.append(operation)
    ComptaOperation.objects.bulk_update(liste_modifications, ["releve"], batch_size=50)
