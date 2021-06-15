# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views import crud
from core.models import Famille, Prestation, Reglement
from django.db.models import Sum
from decimal import Decimal
from core.views.customdatatable import CustomDatatable, Colonne, ColonneAction


class Page(crud.Page):
    menu_code = "liste_soldes"


class Liste(Page, crud.CustomListe):
    filtres = ["fpresent:idfamille", "famille", "solde", "prestations", "reglements"]
    colonnes = [
        Colonne(code="famille", label="Famille", classe="CharField", label_filtre="Nom"),
        Colonne(code="solde", label="Solde", classe="DecimalField"),
        Colonne(code="prestations", label="Prestations", classe="DecimalField", label_filtre="Total"),
        Colonne(code="reglements", label="Règlements", classe="DecimalField", label_filtre="Total"),
        Colonne(code="actions", label="Actions"),
    ]

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Liste des soldes"
        context['box_titre'] = "Liste des soldes des familles"
        context['box_introduction'] = "Voici ci-dessous la liste des soldes des familles."
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context["datatable"] = self.Get_customdatatable()
        context["hauteur_table"] = "400px"
        return context

    def Get_customdatatable(self):
        # Calcul des soldes
        familles = Famille.objects.filter(self.Get_selections_filtres(noms=["idfamille__in"], filtres=self.Get_filtres("Q")))
        dict_prestations = {temp["famille"]: temp["total"] for temp in Prestation.objects.values('famille').annotate(total=Sum("montant"))}
        dict_reglements = {temp["famille"]: temp["total"] for temp in Reglement.objects.values('famille').annotate(total=Sum("montant"))}

        lignes = []
        for famille in familles:
            total_prestations = dict_prestations.get(famille.pk, Decimal(0))
            total_reglements = dict_reglements.get(famille.pk, Decimal(0))
            solde = total_reglements - total_prestations
            colonne_action = ColonneAction()
            colonne_action.Ajouter(url=reverse("famille_resume", args=[famille.pk]), title="Ouvrir la fiche famille", image="ouvrir")
            ligne = [famille.nom, "%0.2f" % solde, "%0.2f" % total_prestations, "%0.2f" % total_reglements, colonne_action]
            lignes.append(ligne)
        return CustomDatatable(colonnes=self.colonnes, lignes=lignes, filtres=self.Get_filtres())

