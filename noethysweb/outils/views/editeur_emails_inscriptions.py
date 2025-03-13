# -*- coding: utf-8 -*-
#  Copyright (c) 2025 Faouzia TEKAYA.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging

logger = logging.getLogger(__name__)
from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from django.db.models import Q
from core.models import Mail, DocumentJoint, Inscription, Destinataire
from django.http import JsonResponse
from django.contrib import messages
import json

def Impression_pdf(request):
    # Récupération des inscriptions cochées
    inscriptions_cochees = json.loads(request.POST.get("inscriptions_cochees"))
    if not inscriptions_cochees:
        return JsonResponse({"erreur": "Veuillez cocher au moins une inscription dans la liste"}, status=401)

    # Création des PDF
    from fiche_individu.utils import utils_inscriptions
    inscription = utils_inscriptions.Inscriptions()
    resultat = inscription.Impression(liste_inscriptions=inscriptions_cochees, dict_options={}, mode_email=True)

    if not resultat:
        return JsonResponse({"success": False}, status=401)

    # Création du mail
    logger.debug("Création d'un nouveau mail...")
    mail = Mail.objects.create(
        categorie="inscription",
        objet="Notification d'inscription",
        html="",
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
            destinataire = Destinataire.objects.create(categorie="famille", famille=cotisation.famille,adresse=cotisation.famille.mail)
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
    url_liste = "editeur_emails_inscriptions"
    menu_code = "editeur_emails_inscriptions"

from outils.views.editeur_emails import Page_destinataires
class Liste(Page_destinataires, crud.Liste):
    template_name = "outils/editeur_emails_inscriptions.html"
    model = Inscription
    categorie = "inscriptions"

    def get_queryset(self):
        condition = Q(activite__structure__in=self.request.user.structures.all())
        return Inscription.objects.select_related("famille", "individu", "groupe", "categorie_tarif",
                                                  "activite").filter(condition)

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Envoi des Inscriptions par Email"
        context['box_titre'] = "Envoyer des Inscriptions par Email en lot"
        context['box_introduction'] = "Cochez des inscriptions puis cliquez sur le bouton Aperçu."
        context['onglet_actif'] = "inscriptions_email"
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        return context

    class datatable_class(MyDatatable):
        filtres = ["igenerique:individu", "fgenerique:famille", 'idinscription', 'date_debut', 'date_fin',
                   'activite__nom', 'groupe__nom', 'statut', 'categorie_tarif__nom']
        check = columns.CheckBoxSelectColumn(label="")
        activite = columns.TextColumn("Activité", sources=['activite__nom'])
        groupe = columns.TextColumn("Groupe", sources=['groupe__nom'])
        categorie_tarif = columns.TextColumn("Catégorie de tarif", sources=['categorie_tarif__nom'])
        individu = columns.CompoundColumn("Individu", sources=['individu__nom', 'individu__prenom'])
        famille = columns.TextColumn("Famille", sources=['famille__nom'])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idinscription", 'date_debut', 'date_fin', 'individu', 'famille', 'activite', 'groupe',
                       'categorie_tarif', 'statut']
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