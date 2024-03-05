# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.db.models import Sum
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Reglement, Ventilation, Prestation
from core.utils import utils_preferences


class Page(crud.Page):
    model = Reglement
    menu_code = "liste_detaillee_reglements"


class Liste(Page, crud.Liste):
    model = Reglement

    def get_queryset(self):
        return Reglement.objects.select_related('mode', 'emetteur', 'famille', 'payeur', 'depot').filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Liste détaillée des règlements"
        context['box_titre'] = "Liste détaillée des règlements des familles"
        context['box_introduction'] = "Voici ci-dessous la liste détaillée des règlements des familles."
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context["totaux"] = json.dumps(["montant"])
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:famille", "idreglement", "date", "mode__label", "emetteur__nom", "numero_piece", "payeur__nom", "montant", "depot__nom"]
        mode = columns.TextColumn("Mode", sources=['mode__label'])
        emetteur = columns.CompoundColumn("Emetteur", sources=['emetteur__nom'])
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        payeur = columns.TextColumn("Payeur", sources=['payeur__nom'])
        depot = columns.TextColumn("Dépôt", sources=['depot__nom'])
        factures = columns.TextColumn("Factures associées", sources=None, processor='Get_factures')
        prestations = columns.TextColumn("Prestations associées", sources=None, processor='Get_prestations')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idreglement", "date", "mode", "emetteur", "numero_piece", "famille", "payeur", "montant", "depot", "factures", "prestations"]
            processors = {
                'date': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ["date"]
            footer = True

        def Get_factures(self, instance, *args, **kwargs):
            factures = Prestation.objects.values('facture__numero').filter(ventilation__reglement=instance.pk, facture__isnull=False).annotate(total=Sum("montant"))
            return ", ".join(["n°%s (%0.2f %s)" % (x["facture__numero"], x["total"], utils_preferences.Get_symbole_monnaie()) for x in factures])

        def Get_prestations(self, instance, *args, **kwargs):
            ventilations = Ventilation.objects.values('prestation__label').filter(reglement=instance.pk).annotate(total=Sum("montant"))
            return ", ".join(["%s (%0.2f %s)" % (x["prestation__label"], x["total"], utils_preferences.Get_symbole_monnaie()) for x in ventilations])
