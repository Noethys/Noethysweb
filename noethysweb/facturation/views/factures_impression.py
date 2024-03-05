# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.http import JsonResponse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Facture
from core.utils import utils_preferences
from core.models import MessageFacture, ModeleImpression
from facturation.forms.factures_options_impression import Formulaire as Form_parametres
from facturation.forms.factures_choix_modele import Formulaire as Form_modele
from facturation.forms.choix_modele_impression import Formulaire as Form_modele_impression


def Impression_pdf(request):
    # Récupération des factures cochées
    factures_cochees = json.loads(request.POST.get("factures_cochees"))
    if not factures_cochees:
        return JsonResponse({"erreur": "Veuillez cocher au moins une facture dans la liste"}, status=401)

    # Récupération du modèle d'impression
    valeurs_form_modele_impression = json.loads(request.POST.get("form_modele_impression"))
    IDmodele_impression = int(valeurs_form_modele_impression.get("modele_impression", 0))

    if IDmodele_impression:
        modele_impression = ModeleImpression.objects.get(pk=IDmodele_impression)
        dict_options = json.loads(modele_impression.options)
        dict_options["modele"] = modele_impression.modele_document
    else:
        # Récupération du modèle de document
        valeurs_form_modele = json.loads(request.POST.get("form_modele_document"))
        form_modele = Form_modele(valeurs_form_modele)
        if not form_modele.is_valid():
            return JsonResponse({"erreur": "Veuillez sélectionner un modèle de document"}, status=401)

        # Récupération des options d'impression
        valeurs_form_parametres = json.loads(request.POST.get("form_parametres"))
        form_parametres = Form_parametres(valeurs_form_parametres, request=request)
        if not form_parametres.is_valid():
            return JsonResponse({"erreur": "Veuillez compléter les options d'impression"}, status=401)

        dict_options = form_parametres.cleaned_data
        dict_options.update(form_modele.cleaned_data)

    # Création du PDF
    from facturation.utils import utils_facturation
    facturation = utils_facturation.Facturation()
    resultat = facturation.Impression(liste_factures=factures_cochees, dict_options=dict_options)
    if not resultat:
        return JsonResponse({"success": False}, status=401)
    return JsonResponse({"nom_fichier": resultat["nom_fichier"]})



class Page(crud.Page):
    model = Facture
    url_liste = "factures_impression"
    menu_code = "factures_impression"


class Liste(Page, crud.Liste):
    template_name = "facturation/factures_impression.html"
    model = Facture

    def get_queryset(self):
        return Facture.objects.select_related('famille', 'lot', 'prefixe').filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Gestion des factures"
        context['box_titre'] = "Imprimer des factures"
        context['box_introduction'] = "Cochez des factures, ajustez si besoin les options d'impression puis cliquez sur le bouton Aperçu."
        context['onglet_actif'] = "factures_impression"
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        context["hauteur_table"] = "400px"
        context['form_modele_document'] = Form_modele()
        context['form_modele_impression'] = Form_modele_impression(categorie="facture")
        context['form_parametres'] = Form_parametres(request=self.request)
        context["messages"] = MessageFacture.objects.all().order_by("titre")
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:famille", 'idfacture', 'date_edition', 'prefixe', 'numero', 'date_debut', 'date_fin', 'total', 'solde', 'solde_actuel', 'lot__nom', 'famille__email_factures']
        check = columns.CheckBoxSelectColumn(label="")
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        solde_actuel = columns.TextColumn("Solde actuel", sources=['solde_actuel'], processor='Get_solde_actuel')
        lot = columns.TextColumn("Lot", sources=['lot__nom'])
        numero = columns.CompoundColumn("Numéro", sources=['prefixe__prefixe', 'numero'])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', 'idfacture', 'date_edition', 'numero', 'date_debut', 'date_fin', 'famille', 'total', 'solde', 'solde_actuel', 'lot']
            processors = {
                'date_edition': helpers.format_date('%d/%m/%Y'),
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
                'date_echeance': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ["date_edition"]

        def Get_solde_actuel(self, instance, **kwargs):
            if instance.etat == "annulation":
                return "<span class='text-red'><i class='fa fa-trash'></i> Annulée</span>"
            icone = "fa-check text-green" if instance.solde_actuel == 0 else "fa-close text-red"
            return "<i class='fa %s margin-r-5'></i>  %0.2f %s" % (icone, instance.solde_actuel, utils_preferences.Get_symbole_monnaie())
