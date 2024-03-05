# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import PesLot, PesPiece, Facture, Mandat, Activite
from core.utils import utils_preferences
import json


class Liste(crud.Page, crud.Liste):
    template_name = "facturation/lots_pes_factures.html"
    menu_code = "lots_pes_liste"
    model = Facture
    objet_pluriel = "des pièces d'export"

    def get_queryset(self):
        return Facture.objects.select_related('famille', 'lot', 'prefixe').filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['box_titre'] = "Sélection de factures"
        context['box_introduction'] = "Sélectionnez des factures ci-dessous."
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        context["hauteur_table"] = "400px"
        context['idlot'] = self.kwargs.get("idlot")
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:pk", 'fprelevement_actif:famille__mandats__actif', 'idfacture', 'date_edition', 'prefixe', 'numero', 'date_debut', 'date_fin', 'total', 'solde', 'solde_actuel', 'lot__nom']
        check = columns.CheckBoxSelectColumn(label="")
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        solde_actuel = columns.TextColumn("Solde actuel", sources=['solde_actuel'], processor='Get_solde_actuel')
        lot = columns.TextColumn("Lot", sources=['lot__nom'])
        numero = columns.CompoundColumn("Numéro", sources=['prefixe__prefixe', 'numero'])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idfacture", 'date_edition', 'numero', 'date_debut', 'date_fin', 'famille', 'total', 'solde', 'solde_actuel', 'lot']
            processors = {
                'date_edition': helpers.format_date('%d/%m/%Y'),
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ["idfacture"]

        def Get_solde_actuel(self, instance, **kwargs):
            if instance.etat == "annulation":
                return "<span class='text-red'><i class='fa fa-trash'></i> Annulée</span>"
            icone = "fa-check text-green" if instance.solde_actuel == 0 else "fa-close text-red"
            return "<i class='fa %s margin-r-5'></i>  %0.2f %s" % (icone, instance.solde_actuel, utils_preferences.Get_symbole_monnaie())

    def post(self, request, **kwargs):
        # Génération des pièces
        idlot = self.kwargs.get("idlot")
        liste_selections = json.loads(request.POST.get("selections"))
        Generation_pieces(idlot=idlot, liste_idfacture=liste_selections)

        return HttpResponseRedirect(reverse_lazy("lots_pes_consulter", kwargs={'pk': idlot}))


def Generation_pieces(idlot=None, liste_idfacture=[]):
    # Importation des factures
    factures = Facture.objects.select_related("famille", "famille__titulaire_helios", "famille__tiers_solidaire").filter(pk__in=liste_idfacture)

    # Importation des mandats
    dict_mandats = {mandat.famille: mandat for mandat in Mandat.objects.filter(famille__in=[facture.famille_id for facture in factures], actif=True)}

    # Importation des activités
    dict_structures_activites = {activite.pk: activite.structure for activite in Activite.objects.select_related("structure").all()}

    # Création des pièces
    liste_ajouts = []
    for facture in factures:
        params = {"lot_id": idlot, "famille_id": facture.famille_id, "type": "facture", "facture": facture, "montant": facture.solde_actuel,
                  "titulaire_helios": facture.famille.titulaire_helios, "tiers_solidaire": facture.famille.tiers_solidaire}
        mandat = dict_mandats.get(facture.famille, None)

        # Vérifie que ce mandat peut être utilisé pour payer cette facture (structure compatible)
        if mandat and mandat.structures.all() and facture.activites:
            for idactivite in [int(idactivite) for idactivite in facture.activites.split(";")]:
                if dict_structures_activites[idactivite] not in mandat.structures.all():
                    mandat = None
                    break

        # Mémorise le mandat pour activer le prélèvement
        if mandat:
            params.update({"prelevement": True, "prelevement_mandat": mandat, "prelevement_sequence": mandat.sequence})
            mandat.Actualiser(ajouter=True)
        liste_ajouts.append(PesPiece(**params))

    # Enregistrement des pièces
    PesPiece.objects.bulk_create(liste_ajouts)
