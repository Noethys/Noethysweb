# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Reglement
from core.utils import utils_preferences
from django.db.models import Q

class Page(crud.Page):
    model = Reglement
    menu_code = "liste_reglements"
    url_liste = "liste_reglements"
    objet_pluriel = "des règlements"
    url_supprimer_plusieurs = "reglements_supprimer_plusieurs"


class Liste(Page, crud.Liste):
    model = Reglement

    def get_queryset(self):
        return Reglement.objects.select_related('mode', 'emetteur', 'famille', 'payeur', 'depot').filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Liste des règlements"
        context['box_titre'] = "Liste des règlements des familles"
        context['box_introduction'] = "Voici ci-dessous la liste des règlements des familles."
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['active_checkbox'] = True
        context['totaux'] = json.dumps(["montant",])
        return context

    class datatable_class(MyDatatable):
        filtres = ["fpresent:famille", "fscolarise:famille", "idreglement", "date", "mode__label", "emetteur__nom", "numero_piece", "famille__nom", "payeur__nom", "montant",
                   "observations", "numero_quittancier", "depot__nom", "compte__nom", "date_differe"]
        check = columns.CheckBoxSelectColumn(label="")
        mode = columns.TextColumn("Mode", sources=['mode__label'])
        emetteur = columns.CompoundColumn("Emetteur", sources=['emetteur__nom'])
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        payeur = columns.TextColumn("Payeur", sources=['payeur__nom'])
        depot = columns.TextColumn("Dépôt", sources=['depot__nom'])
        compte = columns.TextColumn("Compte", sources=['compte__nom'])
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', "idreglement", "date", "mode", "emetteur", "numero_piece", "famille", "payeur", "montant", "depot", "observations", "numero_quittancier",
                       "compte", "date_differe"]
            hidden_columns = ["observations", "numero_quittancier", "compte", "date_differe"]
            processors = {
                "date": helpers.format_date("%d/%m/%Y"),
                "date_differe": helpers.format_date("%d/%m/%Y"),
            }
            ordering = ["date"]
            footer = True

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_modifier(url=reverse("famille_reglements_modifier", kwargs={"idfamille": instance.famille_id, "pk": instance.pk})),
            ]
            return self.Create_boutons_actions(html)

class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
    pass
