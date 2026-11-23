# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.http import JsonResponse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Prestation
from facturation.utils import utils_codes_prestations


def Modifier_codes(request):
    """ Modification par lot des codes analytique et comptable des prestations cochées """
    if not request.user.has_perm("core.liste_prestations"):
        return JsonResponse({"erreur": "Vous n'avez pas accès à cette fonctionnalité"}, status=401)
    try:
        pks = [int(pk) for pk in json.loads(request.POST.get("liste_lignes", "[]"))]
    except (ValueError, TypeError):
        return JsonResponse({"erreur": "Sélection invalide"}, status=401)
    if not pks:
        return JsonResponse({"erreur": "Cochez au moins une prestation"}, status=401)
    parametres = {
        "code_analytique": request.POST.get("code_analytique"), "effacer_code_analytique": request.POST.get("effacer_code_analytique") == "true",
        "code_compta": request.POST.get("code_compta"), "effacer_code_compta": request.POST.get("effacer_code_compta") == "true",
    }
    if not any((utils_codes_prestations.Nettoyer_code(parametres["code_analytique"]), parametres["effacer_code_analytique"],
                utils_codes_prestations.Nettoyer_code(parametres["code_compta"]), parametres["effacer_code_compta"])):
        return JsonResponse({"erreur": "Saisissez au moins un code"}, status=401)
    nbre = utils_codes_prestations.Modifier_codes(pks=pks, **parametres)
    return JsonResponse({"succes": True, "nbre": nbre})


class Page(crud.Page):
    model = Prestation
    url_liste = "liste_prestations"
    menu_code = "liste_prestations"
    description_liste = "Voici ci-dessous la liste des prestations."
    description_saisie = "Saisissez toutes les informations concernant la prestation à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une prestation"
    objet_pluriel = "des prestations"
    url_supprimer_plusieurs = "prestations_supprimer_plusieurs"


class Liste(Page, crud.Liste):
    model = Prestation
    template_name = "facturation/liste_prestations.html"

    def get_queryset(self):
        return Prestation.objects.select_related('activite', 'famille', 'individu', 'tarif', 'facture').filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        context['active_checkbox'] = True
        context['totaux'] = json.dumps(["quantite", "montant"])
        context['boutons_coches'] = json.dumps([
            {"id": "bouton_modifier_codes", "action": "ouvrir_modal_codes()", "title": "Modifier le code analytique et le code comptable des prestations cochées",
             "label": "<i class='fa fa-tag margin-r-5'></i>Modifier les codes"},
        ])
        return context

    class datatable_class(MyDatatable):
        filtres = ["igenerique:individu", "fgenerique:famille", "idprestation", "date", "label", "montant", "activite__nom", "tarif__idtarif", "tarif__date_debut", "facture__idfacture", "code_compta", "code_analytique"]
        check = columns.CheckBoxSelectColumn(label="")
        activite = columns.TextColumn("Activité", sources=['activite__nom'])
        individu = columns.CompoundColumn("Individu", sources=['individu__nom', 'individu__prenom'])
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        tarif = columns.TextColumn("ID Tarif", sources=['tarif__idtarif'])
        tarif_date_debut = columns.TextColumn("Tarif Début", sources=['tarif__date_debut'], processor=helpers.format_date("%d/%m/%Y"))
        facture = columns.TextColumn("Facture", sources=["facture__numero"])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', "idprestation", "date", "label", "quantite", "montant", "activite", "famille", "individu", "tarif", "tarif_date_debut", "facture", "code_compta", "code_analytique"]
            processors = {
                "date": helpers.format_date("%d/%m/%Y"),
                "montant": "Formate_montant_standard",
            }
            ordering = ["date"]
            hidden_columns = ["quantite", "code_compta", "code_analytique"]
            footer = True


class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
    pass
