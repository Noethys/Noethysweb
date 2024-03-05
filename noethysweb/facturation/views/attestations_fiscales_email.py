# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json, time
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.contrib import messages
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.utils import utils_texte
from core.models import Mail, DocumentJoint, AttestationFiscale, Destinataire, ModeleEmail, ModeleImpression
from facturation.forms.attestations_fiscales_options_impression import Formulaire as Form_parametres
from facturation.forms.attestations_fiscales_choix_modele import Formulaire as Form_modele_document
from facturation.forms.choix_modele_impression import Formulaire as Form_modele_impression


def Impression_pdf(request):
    time.sleep(1)

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
    resultat = facturation.Impression(liste_attestations_fiscales=attestations_fiscales_coches, dict_options=dict_options, mode_email=True)
    if not resultat:
        return JsonResponse({"success": False}, status=401)

    # Création du mail
    logger.debug("Création d'un nouveau mail...")
    modele_email = ModeleEmail.objects.filter(categorie="attestation_fiscale", defaut=True).first()
    mail = Mail.objects.create(
        categorie="attestation_fiscale",
        objet=modele_email.objet if modele_email else "",
        html=modele_email.html if modele_email else "",
        adresse_exp=request.user.Get_adresse_exp_defaut(),
        selection="NON_ENVOYE",
        verrouillage_destinataires=True,
        utilisateur=request.user,
    )

    # Création des destinataires et des documents joints
    logger.debug("Enregistrement des destinataires et documents joints...")
    liste_anomalies = []
    for IDattestation, donnees in resultat["noms_fichiers"].items():
        attestation = AttestationFiscale.objects.select_related('famille').get(pk=IDattestation)
        if attestation.famille.mail:
            destinataire = Destinataire.objects.create(categorie="famille", famille=attestation.famille, adresse=attestation.famille.mail, valeurs=json.dumps(donnees["valeurs"]))
            document_joint = DocumentJoint.objects.create(nom="Attestation fiscale", fichier=donnees["nom_fichier"])
            destinataire.documents.add(document_joint)
            mail.destinataires.add(destinataire)
        else:
            liste_anomalies.append(attestation.famille.nom)

    if liste_anomalies:
        messages.add_message(request, messages.ERROR, "Adresses mail manquantes : %s" % ", ".join(liste_anomalies))

    # Création de l'URL pour ouvrir l'éditeur d'emails
    logger.debug("Redirection vers l'éditeur d'emails...")
    url = reverse_lazy("editeur_emails", kwargs={'pk': mail.pk})
    return JsonResponse({"url": url})


class Page(crud.Page):
    model = AttestationFiscale
    url_liste = "attestations_fiscales_impression"
    menu_code = "attestations_fiscales_impression"


class Liste(Page, crud.Liste):
    template_name = "facturation/attestations_fiscales_email.html"
    model = AttestationFiscale

    def get_queryset(self):
        return AttestationFiscale.objects.select_related('famille', 'lot').filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Gestion des attestations fiscales"
        context['box_titre'] = "Envoyer des attestations fiscales par Email"
        context['box_introduction'] = "Cochez des attestations fiscales, ajustez si besoin les options d'impression puis cliquez sur le bouton Transférer."
        context['onglet_actif'] = "attestations_fiscales_email"
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
