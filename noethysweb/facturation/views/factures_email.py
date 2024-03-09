# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.utils import utils_preferences
from core.models import MessageFacture, Mail, DocumentJoint, Facture, Destinataire, ModeleEmail, ModeleImpression, Individu
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

    # Création des PDF
    from facturation.utils import utils_facturation
    facturation = utils_facturation.Facturation()
    resultat = facturation.Impression(liste_factures=factures_cochees, dict_options=dict_options, mode_email=True)
    if not resultat:
        return JsonResponse({"success": False}, status=401)

    # Création du mail
    logger.debug("Création d'un nouveau mail...")
    modele_email = ModeleEmail.objects.filter(categorie="facture", defaut=True).first()
    mail = Mail.objects.create(
        categorie="facture",
        objet=modele_email.objet if modele_email else "",
        html=modele_email.html if modele_email else "",
        adresse_exp=request.user.Get_adresse_exp_defaut(),
        selection="NON_ENVOYE",
        verrouillage_destinataires=True,
        utilisateur=request.user,
    )

    # Importation des factures et des mails des individus
    dict_factures = {facture.pk: facture for facture in Facture.objects.select_related("famille").filter(pk__in=list(resultat["noms_fichiers"].keys()))}
    dict_mails = {individu.pk: {"perso": individu.mail, "travail": individu.travail_mail} for individu in Individu.objects.filter((Q(mail__isnull=False) or Q(travail_mail__isnull=False)))}

    # Recherche des mails des destinataires
    for IDfacture, facture in dict_factures.items():
        facture.liste_mails = []
        if facture.famille.email_factures:
            if ";" in (facture.famille.email_factures_adresses or ""):
                for valeur in facture.famille.email_factures_adresses.split("##"):
                    IDindividu, categorie, adresse = valeur.split(";")
                    if IDindividu and int(IDindividu) in dict_mails:
                        adresse = dict_mails[int(IDindividu)][categorie]
                    if adresse:
                        facture.liste_mails.append(adresse)
            else:
                if facture.famille.mail:
                    facture.liste_mails.append(facture.famille.mail)
        else:
            if facture.famille.mail:
                facture.liste_mails.append(facture.famille.mail)

    # Création des destinataires et des documents joints
    logger.debug("Enregistrement des destinataires et documents joints...")
    liste_anomalies = []
    for IDfacture, donnees in resultat["noms_fichiers"].items():
        facture = dict_factures[IDfacture]
        if facture.liste_mails:
            for adresse in facture.liste_mails:
                destinataire = Destinataire.objects.create(categorie="famille", famille=facture.famille, adresse=adresse, valeurs=json.dumps(donnees["valeurs"]))
                document_joint = DocumentJoint.objects.create(nom="Facture n°%s" % facture.numero, fichier=donnees["nom_fichier"])
                destinataire.documents.add(document_joint)
                mail.destinataires.add(destinataire)
        else:
            liste_anomalies.append(facture.famille.nom)

    if liste_anomalies:
        messages.add_message(request, messages.ERROR, "Adresses mail manquantes : %s" % ", ".join(liste_anomalies))

    # Création de l'URL pour ouvrir l'éditeur d'emails
    logger.debug("Redirection vers l'éditeur d'emails...")
    url = reverse_lazy("editeur_emails", kwargs={'pk': mail.pk})
    return JsonResponse({"url": url})



class Page(crud.Page):
    model = Facture
    url_liste = "factures_email"
    menu_code = "factures_email"


class Liste(Page, crud.Liste):
    template_name = "facturation/factures_email.html"
    model = Facture

    def get_queryset(self):
        return Facture.objects.select_related('famille', 'lot', 'prefixe').filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Gestion des factures"
        context['box_titre'] = "Envoyer des factures par Email"
        context['box_introduction'] = "Cochez des factures, ajustez si besoin les options d'impression puis cliquez sur le bouton Transférer."
        context['onglet_actif'] = "factures_email"
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
