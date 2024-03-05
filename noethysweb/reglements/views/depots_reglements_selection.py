# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Depot, Reglement
from core.utils import utils_preferences


class Liste(crud.Page, crud.Liste):
    template_name = "reglements/depots_reglements_selection.html"
    menu_code = "depots_reglements_liste"
    model = Reglement
    objet_pluriel = "des règlements"

    def get_queryset(self):
        depot = Depot.objects.get(pk=self.kwargs["iddepot"])
        return Reglement.objects.select_related('mode', 'emetteur', 'famille', 'payeur').filter(self.Get_filtres("Q"), depot__isnull=True, compte=depot.compte)

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['box_titre'] = "Sélection des règlements"
        context['box_introduction'] = "Cochez les règlements à inclure dans le dépôt et cliquez sur le bouton Ajouter."
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        context["hauteur_table"] = "400px"
        context['iddepot'] = self.kwargs.get("iddepot")
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:famille", "idreglement", "date", "mode__label", "emetteur__nom", "numero_piece", "payeur__nom",
                   "montant", "compte", "date_differe", "observations"]
        check = columns.CheckBoxSelectColumn(label="")
        mode = columns.TextColumn("Mode", sources=['mode__label'])
        emetteur = columns.CompoundColumn("Emetteur", sources=['emetteur__nom'])
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        payeur = columns.TextColumn("Payeur", sources=['payeur__nom'])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idreglement", "date", "mode", "emetteur", "numero_piece", "montant", "famille", "payeur", "date_differe", "compte", "observations"]
            hidden_columns = ["compte", "observations"]
            processors = {
                "date": helpers.format_date('%d/%m/%Y'),
                "date_differe": helpers.format_date('%d/%m/%Y'),
                "montant": "Formate_montant",
            }
            labels = {
                "date_differe": "Différé",
            }
            ordering = ["-idreglement"]

        def Formate_montant(self, instance, **kwargs):
            return "%0.2f %s" % (instance.montant, utils_preferences.Get_symbole_monnaie())

    def post(self, request, **kwargs):
        iddepot = self.kwargs.get("iddepot")
        liste_selections = json.loads(request.POST.get("selections"))
        Enregistrement_reglements(iddepot=iddepot, liste_idreglement=liste_selections)
        return HttpResponseRedirect(reverse_lazy("depots_reglements_consulter", kwargs={'pk': iddepot}))


def Enregistrement_reglements(iddepot=None, liste_idreglement=[]):
    # Importation des données
    depot = Depot.objects.get(pk=iddepot)
    nouveaux_reglements = Reglement.objects.filter(pk__in=liste_idreglement)

    # Modification du nouveau règlement à associer au dépôt
    liste_modifications = []
    for reglement in nouveaux_reglements:
        reglement.depot = depot
        liste_modifications.append(reglement)
    Reglement.objects.bulk_update(liste_modifications, ["depot"], batch_size=50)

    # Enregistrement du montant total dans le dépôt
    depot.Maj_montant()
