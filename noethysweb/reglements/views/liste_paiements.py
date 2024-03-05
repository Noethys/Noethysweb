# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Paiement
from core.utils import utils_texte


class Page(crud.Page):
    model = Paiement
    menu_code = "liste_paiements"
    url_liste = "liste_paiements"
    objet_pluriel = "des paiements en ligne"


class Liste(Page, crud.Liste):
    model = Paiement

    def get_queryset(self):
        return Paiement.objects.select_related("famille").prefetch_related("reglements").filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Liste des paiements en ligne"
        context['box_titre'] = "Liste des paiements en ligne"
        context['box_introduction'] = "Voici ci-dessous la liste des paiements en ligne. Vous y trouverez tous les paiements réalisés sur le portail, qu'ils aient été réussis ou non."
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:famille", "idpaiement", "horodatage", "montant"]
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        reglements = columns.TextColumn("Règlements", sources=["reglements__pk"], processor='Get_reglements')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idpaiement", "horodatage", "famille", "montant", "systeme_paiement", "idtransaction", "saisie", "resultat", "message", "reglements"]
            processors = {
                "horodatage": helpers.format_date("%d/%m/%Y %H:%M"),
                "montant": "Formate_montant",
            }
            labels = {
                "systeme_paiement": "Système",
            }
            ordering = ["horodatage"]

        def Formate_montant(self, instance, **kwargs):
            return utils_texte.Formate_montant(instance.montant)

        def Get_reglements(self, instance, *args, **kwargs):
            return ", ".join(["ID%d" % reglement.pk for reglement in instance.reglements.all()])
