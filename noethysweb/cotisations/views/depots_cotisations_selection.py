# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import DepotCotisations, Cotisation
from core.utils import utils_preferences


class Liste(crud.Page, crud.Liste):
    template_name = "cotisations/depots_cotisations_selection.html"
    menu_code = "depots_cotisations_liste"
    model = Cotisation
    objet_pluriel = "des adhésions"

    def get_queryset(self):
        return Cotisation.objects.select_related('famille', 'individu', 'type_cotisation', 'type_cotisation__structure', 'unite_cotisation', 'depot_cotisation').filter(self.Get_filtres("Q"), depot_cotisation__isnull=True)

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['box_titre'] = "Sélection des adhésions"
        context['box_introduction'] = "Cochez les adhésions à inclure dans le dépôt et cliquez sur le bouton Ajouter."
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        context["hauteur_table"] = "400px"
        context['iddepot'] = self.kwargs.get("iddepot")
        return context

    class datatable_class(MyDatatable):
        filtres = ["igenerique:individu", "fgenerique:famille", "idcotisation", "date_saisie", "date_creation_carte", "numero", "date_debut", "date_fin",
                   "observations", "type_cotisation__nom", "unite_cotisation__nom"]
        check = columns.CheckBoxSelectColumn(label="")
        individu = columns.CompoundColumn("Individu", sources=['individu__nom', 'individu__prenom'])
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        nom_cotisation = columns.TextColumn("Nom", sources=['type_cotisation__nom', 'unite_cotisation__nom'], processor='Get_nom_cotisation')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idcotisation", "idcotisation", "date_debut", "date_fin", "famille", "individu", "nom_cotisation", "numero"]
            processors = {
                "date_debut": helpers.format_date('%d/%m/%Y'),
                "date_fin": helpers.format_date('%d/%m/%Y'),
            }
            labels = {
                "date_debut": "Début",
                "date_fin": "Fin",
            }
            ordering = ["-idcotisation"]

        def Get_nom_cotisation(self, instance, *args, **kwargs):
            if instance.prestation:
                return instance.prestation.label
            else:
                return "%s - %s" % (instance.type_cotisation.nom, instance.unite_cotisation.nom)

    def post(self, request, **kwargs):
        iddepot = self.kwargs.get("iddepot")
        liste_selections = json.loads(request.POST.get("selections"))
        Enregistrement_cotisations(iddepot=iddepot, liste_idcotisation=liste_selections)
        return HttpResponseRedirect(reverse_lazy("depots_cotisations_consulter", kwargs={'pk': iddepot}))


def Enregistrement_cotisations(iddepot=None, liste_idcotisation=[]):
    # Importation des données
    depot = DepotCotisations.objects.get(pk=iddepot)
    nouveaux_cotisations = Cotisation.objects.filter(pk__in=liste_idcotisation)

    # Modification de la nouvelle cotisation à associer au dépôt
    liste_modifications = []
    for cotisation in nouveaux_cotisations:
        cotisation.depot_cotisation = depot
        liste_modifications.append(cotisation)
    Cotisation.objects.bulk_update(liste_modifications, ["depot_cotisation"], batch_size=50)

    # Enregistrement de la nouvelle quantité dans le dépôt
    depot.Maj_quantite()
