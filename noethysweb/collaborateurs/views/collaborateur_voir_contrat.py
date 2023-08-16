# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.db.models import Q
from collaborateurs.forms.contrats_choix_modele import Formulaire as Form_modele
from collaborateurs.views.collaborateur import Onglet
from core.models import ContratCollaborateur
from core.utils import utils_fusion_word, utils_dates, utils_questionnaires


def Fusionner(request):
    """ Générer le fichier d'export Word """
    # Récupération du modèle de document Word
    form_modele = Form_modele(json.loads(request.POST.get("form_modele")))
    if not form_modele.is_valid():
        return JsonResponse({"erreur": "Veuillez sélectionner un modèle de document"}, status=401)
    modele_document = form_modele.cleaned_data["modele"]

    # Récupération du contrat
    contrat = ContratCollaborateur.objects.select_related("collaborateur", "type_poste").get(pk=int(request.POST["idcontrat"]))

    # Création des valeurs à fusionner
    valeurs = {
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
    questionnaires_contrats = (utils_questionnaires.ChampsEtReponses(categorie="contrat_collaborateur", filtre_reponses=Q(pk=contrat.pk)), contrat.pk)
    for questionnaire, donnee in (questionnaires_collaborateurs, questionnaires_contrats):
        for dictReponse in questionnaire.GetDonnees(donnee):
            valeurs[dictReponse["champ"]] = dictReponse["reponse"]

    # Fusion du document Word
    fusion = utils_fusion_word.Fusionner(titre="Contrat", modele_document=modele_document, valeurs=valeurs, request=request)
    if fusion.erreurs:
        return JsonResponse({"erreur": fusion.Get_erreurs_html()}, status=401)
    return JsonResponse({"resultat": "ok", "nom_fichier": fusion.Get_nom_fichier()})


class View(Onglet, TemplateView):
    template_name = "collaborateurs/collaborateur_voir_contrat.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['box_titre'] = "Fusionner un contrat vers Word"
        context['box_introduction'] = "Sélectionnez un modèle de document Word et cliquez sur Fusionner."
        context['onglet_actif'] = "contrats"
        context['form_modele'] = Form_modele()
        context['idcollaborateur'] = kwargs.get("idcollaborateur", None)
        context['idcontrat'] = kwargs.get("idcontrat", None)
        return context
