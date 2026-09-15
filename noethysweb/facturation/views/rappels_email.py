# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.contrib import messages
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.utils import utils_texte
from core.models import Mail, DocumentJoint, Rappel, Facture, Destinataire, ModeleEmail, ModeleImpression, ModeleDocument
from facturation.forms.rappels_options_impression import Formulaire as Form_parametres
from facturation.forms.rappels_choix_modele import Formulaire as Form_modele
from facturation.forms.choix_modele_impression import Formulaire as Form_modele_impression
from facturation.forms.factures_options_impression import Formulaire as Form_parametres_facture


def Get_dict_options_facture(request):
    """ Reconstitue des options d'impression par défaut pour les factures (mêmes valeurs mémorisées que
    dans le menu Facturation > Factures > Envoyer par Email), utilisées pour générer les PDF des factures
    impayées jointes aux lettres de rappel. Renvoie None si aucun modèle de document de facture n'est défini. """
    modele = ModeleDocument.objects.filter(categorie="facture", defaut=True).first() or ModeleDocument.objects.filter(categorie="facture").order_by("nom").first()
    if not modele:
        return None
    form_parametres_facture = Form_parametres_facture(request=request)
    dict_options = {nom: champ.initial for nom, champ in form_parametres_facture.fields.items()}
    dict_options["modele"] = modele
    return dict_options


def Get_factures_impayees(famille):
    """ Renvoie la liste des factures impayées (solde actuel positif) d'une famille """
    return list(Facture.objects.filter(famille=famille, solde_actuel__gt=0).exclude(etat="annulation"))


def Impression_pdf(request):
    # Récupération des rappels cochés
    rappels_coches = json.loads(request.POST.get("rappels_coches"))
    if not rappels_coches:
        return JsonResponse({"erreur": "Veuillez cocher au moins une lettre de rappel dans la liste"}, status=401)

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

    # Création des PDF
    from facturation.utils import utils_rappels
    facturation = utils_rappels.Facturation()
    resultat = facturation.Impression(liste_rappels=rappels_coches, dict_options=dict_options, mode_email=True)
    if not resultat:
        return JsonResponse({"success": False}, status=401)

    # Création du mail
    logger.debug("Création d'un nouveau mail...")
    modele_email = ModeleEmail.objects.filter(categorie="rappel", defaut=True).first()
    mail = Mail.objects.create(
        categorie="rappel",
        objet=modele_email.objet if modele_email else "",
        html=modele_email.html if modele_email else "",
        adresse_exp=request.user.Get_adresse_exp_defaut(),
        selection="NON_ENVOYE",
        verrouillage_destinataires=True,
        utilisateur=request.user,
    )

    # Détermine si les factures impayées doivent être jointes aux emails
    joindre_factures_impayees = dict_options.get("joindre_factures_impayees", True)
    dict_options_facture = Get_dict_options_facture(request) if joindre_factures_impayees else None
    if joindre_factures_impayees and not dict_options_facture:
        logger.warning("Aucun modèle de document de facture n'est défini : les factures impayées ne seront pas jointes.")

    # Création des destinataires et des documents joints
    logger.debug("Enregistrement des destinataires et documents joints...")
    liste_anomalies = []
    from facturation.utils import utils_facturation
    for IDrappel, donnees in resultat["noms_fichiers"].items():
        rappel = Rappel.objects.select_related('famille').get(pk=IDrappel)
        if rappel.famille.mail:
            destinataire = Destinataire.objects.create(categorie="famille", famille=rappel.famille, adresse=rappel.famille.mail, valeurs=json.dumps(donnees["valeurs"]))
            document_joint = DocumentJoint.objects.create(nom="Lettre de rappel", fichier=donnees["nom_fichier"])
            destinataire.documents.add(document_joint)

            # Joint les factures impayées de la famille
            if dict_options_facture:
                factures_impayees = Get_factures_impayees(rappel.famille)
                if factures_impayees:
                    facturation = utils_facturation.Facturation()
                    resultat_factures = facturation.Impression(liste_factures=[facture.pk for facture in factures_impayees], dict_options=dict_options_facture, mode_email=True)
                    if resultat_factures:
                        dict_factures = {facture.pk: facture for facture in factures_impayees}
                        for IDfacture, donnees_facture in resultat_factures["noms_fichiers"].items():
                            document_joint_facture = DocumentJoint.objects.create(nom="Facture %s" % dict_factures[IDfacture].numero, fichier=donnees_facture["nom_fichier"])
                            destinataire.documents.add(document_joint_facture)

            mail.destinataires.add(destinataire)
        else:
            liste_anomalies.append(rappel.famille.nom)

    if liste_anomalies:
        messages.add_message(request, messages.ERROR, "Adresses mail manquantes : %s" % ", ".join(liste_anomalies))

    # Création de l'URL pour ouvrir l'éditeur d'emails
    logger.debug("Redirection vers l'éditeur d'emails...")
    url = reverse_lazy("editeur_emails", kwargs={'pk': mail.pk})
    return JsonResponse({"url": url})



class Page(crud.Page):
    model = Rappel
    url_liste = "rappels_email"
    menu_code = "rappels_email"


class Liste(Page, crud.Liste):
    template_name = "facturation/rappels_email.html"
    model = Rappel

    def get_queryset(self):
        return Rappel.objects.select_related('famille', 'lot').filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Gestion des lettres de rappel"
        context['box_titre'] = "Envoyer des lettres de rappel par Email"
        context['box_introduction'] = "Cochez des lettres de rappel, ajustez si besoin les options d'impression puis cliquez sur le bouton Transférer."
        context['onglet_actif'] = "rappels_email"
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        context["hauteur_table"] = "400px"
        context['form_modele_document'] = Form_modele()
        context['form_modele_impression'] = Form_modele_impression(categorie="rappel")
        context['form_parametres'] = Form_parametres(request=self.request)
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:famille", 'idrappel', 'date_edition', 'numero', 'famille', 'date_reference', 'solde', 'date_min', 'date_max', 'lot__nom']
        check = columns.CheckBoxSelectColumn(label="")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        solde = columns.TextColumn("Solde", sources=['solde'], processor='Get_solde')
        lot = columns.TextColumn("Lot", sources=['lot__nom'])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', 'idrappel', 'date_edition', 'numero', 'famille', 'solde', 'date_max', 'lot']
            processors = {
                'date_edition': helpers.format_date('%d/%m/%Y'),
                'date_max': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ["date_edition"]

        def Get_solde(self, instance, **kwargs):
            return utils_texte.Formate_montant(instance.solde)

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_imprimer(url=reverse("famille_voir_rappel", kwargs={"idfamille": instance.famille_id, "idrappel": instance.pk}), title="Imprimer ou envoyer par email la lettre de rappel"),
            ]
            return self.Create_boutons_actions(html)
