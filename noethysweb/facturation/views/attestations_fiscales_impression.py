# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.urls import reverse
from django.http import JsonResponse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import AttestationFiscale, ModeleImpression
from core.utils import utils_texte
from facturation.forms.attestations_fiscales_options_impression import Formulaire as Form_parametres
from facturation.forms.attestations_fiscales_choix_modele import Formulaire as Form_modele_document
from facturation.forms.choix_modele_impression import Formulaire as Form_modele_impression


def Impression_pdf(request):
    # Récupération des attestations fiscales cochées
    attestations_fiscales_coches = json.loads(request.POST.get("attestations_fiscales_coches"))
    if not attestations_fiscales_coches:
        return JsonResponse({"erreur": "Veuillez cocher au moins une attestation fiscale dans la liste"}, status=401)

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
        form_modele = Form_modele_document(valeurs_form_modele)
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
    from facturation.utils import utils_attestations_fiscales
    facturation = utils_attestations_fiscales.Facturation()
    resultat = facturation.Impression(liste_attestations_fiscales=attestations_fiscales_coches, dict_options=dict_options)
    if not resultat:
        return JsonResponse({"success": False}, status=401)
    return JsonResponse({"nom_fichier": resultat["nom_fichier"]})


class Page(crud.Page):
    model = AttestationFiscale
    url_liste = "attestations_fiscales_impression"
    menu_code = "attestations_fiscales_impression"


class Liste(Page, crud.Liste):
    template_name = "facturation/attestations_fiscales_impression.html"
    model = AttestationFiscale

    def get_queryset(self):
        return AttestationFiscale.objects.select_related('famille', 'lot').filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Gestion des attestations fiscales"
        context['box_titre'] = "Imprimer des attestations fiscales"
        context['box_introduction'] = "Cochez des attestations fiscales, ajustez si besoin les options d'impression puis cliquez sur le bouton Aperçu."
        context['onglet_actif'] = "attestations_fiscales_impression"
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        context["hauteur_table"] = "400px"
        context['form_modele_document'] = Form_modele_document()
        context['form_modele_impression'] = Form_modele_impression(categorie="attestation_fiscale")
        context['form_parametres'] = Form_parametres(request=self.request)
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:famille", "idattestation", "date_edition", "famille", "numero", "date_debut", "date_fin", "total", "lot__nom"]
        check = columns.CheckBoxSelectColumn(label="")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        total = columns.TextColumn("Total", sources=['total'], processor='Get_total')
        lot = columns.TextColumn("Lot", sources=['lot__nom'])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', "idattestation", "date_edition", "famille", "numero", "date_debut", "date_fin", "total", "lot"]
            processors = {
                'date_edition': helpers.format_date('%d/%m/%Y'),
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ["date_edition"]

        def Get_total(self, instance, **kwargs):
            return utils_texte.Formate_montant(instance.total)

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_imprimer(url=reverse("famille_voir_attestation_fiscale", kwargs={"idfamille": instance.famille_id, "idattestation": instance.pk}), title="Imprimer ou envoyer par email l'attestation fiscale"),
            ]
            return self.Create_boutons_actions(html)
