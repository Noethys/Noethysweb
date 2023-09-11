# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.urls import reverse
from django.http import JsonResponse
from django.db.models import Q
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import ContratCollaborateur
from core.utils import utils_dates, utils_questionnaires, utils_fusion_word
from collaborateurs.forms.contrats_choix_modele import Formulaire as Form_modele


def Fusionner(request):
    # Récupération des contrats cochés
    contrats_coches = json.loads(request.POST.get("contrats_coches"))
    if not contrats_coches:
        return JsonResponse({"erreur": "Veuillez cocher au moins un contrat dans la liste"}, status=401)
    contrats = ContratCollaborateur.objects.select_related("collaborateur", "type_poste").filter(pk__in=contrats_coches)

    # Récupération du modèle de document
    form_modele = Form_modele(json.loads(request.POST.get("form_modele")))
    if not form_modele.is_valid():
        return JsonResponse({"erreur": "Veuillez sélectionner un modèle de document"}, status=401)
    modele_document = form_modele.cleaned_data["modele"]

    # Création des valeurs à fusionner
    valeurs = []
    for contrat in contrats:
        valeurs_contrat = {
            "{CONTRAT_ID}": contrat.pk,
            "{CONTRAT_DATE_DEBUT}": utils_dates.ConvertDateToFR(contrat.date_debut),
            "{CONTRAT_DATE_FIN}": utils_dates.ConvertDateToFR(contrat.date_fin),
            "{CONTRAT_TYPE_POSTE}": contrat.type_poste.nom,
            "{CONTRAT_OBSERVATIONS}": contrat.observations,
            "{COLLABORATEUR_ID}": contrat.collaborateur_id,
            "{COLLABORATEUR_CIVILITE}": contrat.collaborateur.civilite,
            "{COLLABORATEUR_NOM}": contrat.collaborateur.nom,
            "{COLLABORATEUR_NOM_JFILLE}": contrat.collaborateur.nom_jfille,
            "{COLLABORATEUR_PRENOM}": contrat.collaborateur.prenom,
            "{COLLABORATEUR_RUE}": contrat.collaborateur.rue_resid,
            "{COLLABORATEUR_CODE_POSTAL}": contrat.collaborateur.cp_resid,
            "{COLLABORATEUR_VILLE}": contrat.collaborateur.ville_resid,
            "{COLLABORATEUR_TEL_PRO}": contrat.collaborateur.travail_tel,
            "{COLLABORATEUR_MAIL_PRO}": contrat.collaborateur.travail_mail,
            "{COLLABORATEUR_TEL_DOMICILE}": contrat.collaborateur.tel_domicile,
            "{COLLABORATEUR_TEL_PORTABLE}": contrat.collaborateur.tel_mobile,
            "{COLLABORATEUR_MAIL}": contrat.collaborateur.mail,
            "{COLLABORATEUR_MEMO}": contrat.collaborateur.memo,
        }

        # Ajout des questionnaires
        questionnaires_collaborateurs = (utils_questionnaires.ChampsEtReponses(categorie="collaborateur", filtre_reponses=Q(collaborateur_id=contrat.collaborateur_id)), contrat.collaborateur_id)
        questionnaires_contrats = (utils_questionnaires.ChampsEtReponses(categorie="contrat_collaborateur", filtre_reponses=Q(donnee=contrat.pk)), contrat.pk)
        for questionnaire, donnee in (questionnaires_collaborateurs, questionnaires_contrats):
            for dictReponse in questionnaire.GetDonnees(donnee):
                valeurs_contrat[dictReponse["champ"]] = dictReponse["reponse"]

        valeurs.append(valeurs_contrat)

    # Fusion du document Word
    fusion = utils_fusion_word.Fusionner(titre="Contrats", modele_document=modele_document, valeurs=valeurs, request=request)
    if fusion.erreurs:
        return JsonResponse({"erreur": fusion.Get_erreurs_html()}, status=401)
    return JsonResponse({"resultat": "ok", "nom_fichier": fusion.Get_nom_fichier()})


class Page(crud.Page):
    model = ContratCollaborateur
    url_liste = "fusionner_contrats_word"
    menu_code = "fusionner_contrats_word"


class Liste(Page, crud.Liste):
    template_name = "collaborateurs/fusionner_contrats_word.html"
    model = ContratCollaborateur

    def get_queryset(self):
        return ContratCollaborateur.objects.select_related("collaborateur", "type_poste").filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Fusionner des contrats vers Word"
        context['box_titre'] = "Fusionner"
        context['box_introduction'] = "Cochez des contrats, sélectionnez si besoin un modèle de document puis cliquez sur le bouton Fusionner."
        context['onglet_actif'] = "fusionner_contrats_word"
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        context["hauteur_table"] = "400px"
        context['form_modele'] = Form_modele()
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idcontrat", "date_debut", "date_fin", "collaborateur", "type_poste"]
        check = columns.CheckBoxSelectColumn(label="")
        collaborateur = columns.TextColumn("Collaborateur", sources=["collaborateur__nom", "collaborateur__prenom"], processor='Get_nom_collaborateur')
        type_poste = columns.TextColumn("Poste", sources=["type_poste__nom"], processor='Get_nom_type_poste')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idcontrat", "date_debut", "date_fin", "collaborateur", "type_poste"]
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            labels = {
                "date_debut": "Début",
                "date_fin": "Fin",
            }
            ordering = ["date_debut"]

        def Get_nom_collaborateur(self, instance, *args, **kwargs):
            return instance.collaborateur.Get_nom()

        def Get_nom_type_poste(self, instance, *args, **kwargs):
            return instance.type_poste.nom

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_modifier(url=reverse("collaborateur_contrats_modifier", kwargs={"idcollaborateur": instance.collaborateur_id, "pk": instance.pk})),
                self.Create_bouton_supprimer(url=reverse("collaborateur_contrats_supprimer", kwargs={"idcollaborateur": instance.collaborateur_id, "pk": instance.pk})),
            ]
            return self.Create_boutons_actions(html)
