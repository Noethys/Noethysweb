# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from django.db.models import Q
from individus.forms.inscriptions_choix_modele import Formulaire as Form_modele
from core.models import Mail, DocumentJoint, Inscription, Destinataire, AdresseMail, ModeleEmail
from django.http import JsonResponse
from django.contrib import messages
import json


def Impression_pdf(request):
    # Récupération des inscriptions cochées
    inscriptions_cochees = json.loads(request.POST.get("inscriptions_cochees"))
    if not inscriptions_cochees:
        return JsonResponse({"erreur": "Veuillez cocher au moins une inscription dans la liste"}, status=401)

    # Récupération du modèle de document
    valeurs_form_modele = json.loads(request.POST.get("form_modele"))
    form_modele = Form_modele(valeurs_form_modele)
    if not form_modele.is_valid():
        return JsonResponse({"erreur": "Veuillez sélectionner un modèle de document"}, status=401)

    dict_options = form_modele.cleaned_data

    # Création des PDF
    from fiche_individu.utils import utils_inscriptions
    inscription = utils_inscriptions.Inscriptions()
    resultat = inscription.Impression(liste_inscriptions=inscriptions_cochees, dict_options=dict_options, mode_email=True)
    if not resultat:
        return JsonResponse({"success": False}, status=401)

    # Création du mail
    logger.debug("Création d'un nouveau mail...")
    modele_email = ModeleEmail.objects.filter(categorie="inscription", defaut=True).first()
    mail = Mail.objects.create(
        categorie="inscription",
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
    for IDcotisation, donnees in resultat["noms_fichiers"].items():
        cotisation = Inscription.objects.select_related('famille').get(pk=IDcotisation)
        if cotisation.famille.mail:
            destinataire = Destinataire.objects.create(categorie="famille", famille=cotisation.famille, adresse=cotisation.famille.mail, valeurs=json.dumps(donnees["valeurs"]))
            document_joint = DocumentJoint.objects.create(nom="Inscription", fichier=donnees["nom_fichier"])
            destinataire.documents.add(document_joint)
            mail.destinataires.add(destinataire)
        else:
            liste_anomalies.append(cotisation.famille.nom)

    if liste_anomalies:
        messages.add_message(request, messages.ERROR, "Adresses mail manquantes : %s" % ", ".join(liste_anomalies))

    # Création de l'URL pour ouvrir l'éditeur d'emails
    logger.debug("Redirection vers l'éditeur d'emails...")
    url = reverse_lazy("editeur_emails", kwargs={'pk': mail.pk})
    return JsonResponse({"url": url})



class Page(crud.Page):
    model = Inscription
    url_liste = "inscriptions_email"
    menu_code = "inscriptions_email"


class Liste(Page, crud.Liste):
    template_name = "individus/inscriptions_email.html"
    model = Inscription

    def get_queryset(self):
        condition = Q(activite__structure__in=self.request.user.structures.all())
        return Inscription.objects.select_related("famille", "individu", "groupe", "categorie_tarif", "activite").filter(self.Get_filtres("Q"), condition)

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Gestion des inscriptions"
        context['box_titre'] = "Envoyer des inscriptions par Email"
        context['box_introduction'] = "Cochez des inscriptions, sélectionnez si besoin un modèle de document puis cliquez sur le bouton Aperçu."
        context['onglet_actif'] = "inscriptions_email"
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        context['form_modele'] = Form_modele()
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["igenerique:individu", "fgenerique:famille", 'idinscription', 'date_debut', 'date_fin', 'activite__nom', 'groupe__nom', 'statut', 'categorie_tarif__nom']
        check = columns.CheckBoxSelectColumn(label="")
        activite = columns.TextColumn("Activité", sources=['activite__nom'])
        groupe = columns.TextColumn("Groupe", sources=['groupe__nom'])
        categorie_tarif = columns.TextColumn("Catégorie de tarif", sources=['categorie_tarif__nom'])
        individu = columns.CompoundColumn("Individu", sources=['individu__nom', 'individu__prenom'])
        famille = columns.TextColumn("Famille", sources=['famille__nom'])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idinscription", 'date_debut', 'date_fin', 'individu', 'famille', 'activite', 'groupe', 'categorie_tarif', 'statut']
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
                'statut': 'Formate_statut',
            }
            ordering = ['date_debut']

        def Formate_statut(self, instance, *args, **kwargs):
            if instance.statut == "attente":
                return "<i class='fa fa-hourglass-2 text-yellow'></i> Attente"
            elif instance.statut == "refus":
                return "<i class='fa fa-times-circle text-red'></i> Refus"
            else:
                return "<i class='fa fa-check-circle-o text-green'></i> Valide"
