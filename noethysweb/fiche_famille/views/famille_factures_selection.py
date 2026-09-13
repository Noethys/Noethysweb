# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Facture, Prestation
from core.utils import utils_texte, utils_dates, utils_historique
from facturation.utils import utils_factures
from fiche_famille.views.famille import Onglet


class Liste(Onglet, crud.Liste):
    template_name = "fiche_famille/famille_factures_selection.html"
    menu_code = "famille_factures_liste"
    model = Prestation
    objet_pluriel = "des prestations"

    def get_queryset(self):
        return Prestation.objects.select_related("individu", "activite").filter(self.Get_filtres("Q"), facture__isnull=True, famille_id=self.kwargs.get("idfamille"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['box_titre'] = "Sélection des prestations de la facture"
        context['box_introduction'] = "Cochez les prestations à inclure dans la facture et cliquez sur le bouton Ajouter."
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        context["hauteur_table"] = "400px"
        context['idfamille'] = self.kwargs.get("idfamille")
        context['idfacture'] = self.kwargs.get("pk")
        return context

    class datatable_class(MyDatatable):
        filtres = ["idprestation", "date", "individu__nom", "activite__nom", "label", "montant"]
        check = columns.CheckBoxSelectColumn(label="")
        activite = columns.TextColumn("Activité", sources=['activite__nom'])
        label = columns.TextColumn("Label", sources=['label'])
        individu = columns.TextColumn("Individu", sources=["individu__nom", "individu__prenom"], processor="Formate_individu")
        montant = columns.TextColumn("Montant", sources=["montant"], processor="Formate_montant")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idprestation", "date", "individu", "activite", "label", "montant"]
            processors = {
                "date": helpers.format_date("%d/%m/%Y"),
                "montant": "Formate_montant",
            }
            ordering = ["date"]

        def Formate_individu(self, instance, **kwargs):
            return instance.individu.Get_nom() if instance.individu else ""

        def Formate_montant(self, instance, **kwargs):
            return utils_texte.Formate_montant(instance.montant)

    def post(self, request, **kwargs):
        idfacture = self.kwargs.get("pk")
        liste_selections = json.loads(request.POST.get("selections"))
        Enregistrement_prestations(idfacture=idfacture, liste_idprestation=liste_selections, request=request)
        return HttpResponseRedirect(reverse_lazy("famille_factures_consulter", kwargs={"idfamille": self.kwargs["idfamille"], "pk": idfacture}))


def Enregistrement_prestations(idfacture=None, liste_idprestation=[], request=None):
    # Importation des données
    facture = Facture.objects.get(pk=idfacture)
    nouvelles_prestations = Prestation.objects.filter(pk__in=liste_idprestation)

    # Modification des prestations
    liste_modifications = []
    liste_historique = []
    for prestation in nouvelles_prestations:
        prestation.facture = facture
        liste_modifications.append(prestation)
        liste_historique.append({
            "titre": "Ajout d'une prestation dans une facture", "detail": "%s du %s (facture N°%d)" % (prestation.label, utils_dates.ConvertDateToFR(prestation.date), facture.pk),
            "utilisateur": request.user if request else None, "famille_id": prestation.famille_id, "individu_id": prestation.individu_id,
            "objet": "Facture", "idobjet": facture.pk, "classe": "Facture", "activite_id": prestation.activite_id,
        })
    Prestation.objects.bulk_update(liste_modifications, ["facture"], batch_size=50)

    # Sauvegarde de l'historique
    utils_historique.Ajouter_plusieurs(liste_historique)

    # Enregistrement des totaux de la facture
    utils_factures.Maj_total_factures(IDfacture=idfacture)
