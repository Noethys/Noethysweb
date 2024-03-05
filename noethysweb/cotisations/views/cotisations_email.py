# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.utils import utils_dates
from cotisations.forms.cotisations_choix_modele import Formulaire as Form_modele
from core.models import Mail, DocumentJoint, Cotisation, Destinataire, AdresseMail, ModeleEmail
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q
import json


def Impression_pdf(request):
    # Récupération des cotisations cochées
    cotisations_cochees = json.loads(request.POST.get("cotisations_cochees"))
    if not cotisations_cochees:
        return JsonResponse({"erreur": "Veuillez cocher au moins une adhésion dans la liste"}, status=401)

    # Récupération du modèle de document
    valeurs_form_modele = json.loads(request.POST.get("form_modele"))
    form_modele = Form_modele(valeurs_form_modele)
    if not form_modele.is_valid():
        return JsonResponse({"erreur": "Veuillez sélectionner un modèle de document"}, status=401)

    dict_options = form_modele.cleaned_data

    # Création des PDF
    from cotisations.utils import utils_cotisations
    cotis = utils_cotisations.Cotisations()
    resultat = cotis.Impression(liste_cotisations=cotisations_cochees, dict_options=dict_options, mode_email=True)
    if not resultat:
        return JsonResponse({"success": False}, status=401)

    # Création du mail
    logger.debug("Création d'un nouveau mail...")
    modele_email = ModeleEmail.objects.filter(categorie="cotisation", defaut=True).first()
    mail = Mail.objects.create(
        categorie="cotisation",
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
        cotisation = Cotisation.objects.select_related('famille').get(pk=IDcotisation)
        if cotisation.famille.mail:
            destinataire = Destinataire.objects.create(categorie="famille", famille=cotisation.famille, adresse=cotisation.famille.mail, valeurs=json.dumps(donnees["valeurs"]))
            document_joint = DocumentJoint.objects.create(nom="Adhésion", fichier=donnees["nom_fichier"])
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
    model = Cotisation
    url_liste = "cotisations_email"
    menu_code = "cotisations_email"


class Liste(Page, crud.Liste):
    template_name = "cotisations/cotisations_email.html"
    model = Cotisation

    def get_queryset(self):
        condition = (Q(type_cotisation__structure__in=self.request.user.structures.all()) | Q(type_cotisation__structure__isnull=True))
        return Cotisation.objects.select_related('famille', 'individu', 'type_cotisation', 'unite_cotisation', 'depot_cotisation').filter(self.Get_filtres("Q"), condition)

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Gestion des adhésions"
        context['box_titre'] = "Envoyer des adhésions par Email"
        context['box_introduction'] = "Cochez des adhésions, sélectionnez si besoin un modèle de document puis cliquez sur le bouton Aperçu."
        context['onglet_actif'] = "cotisations_email"
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        context["hauteur_table"] = "400px"
        context['form_modele'] = Form_modele()
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["igenerique:individu", "fgenerique:famille", "idcotisation", "date_saisie", "date_creation_carte", "numero", "date_debut", "date_fin", "observations", "type_cotisation__nom", "unite_cotisation__nom", "depot_cotisation__date"]
        check = columns.CheckBoxSelectColumn(label="")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        individu = columns.CompoundColumn("Individu", sources=['individu__nom', 'individu__prenom'])
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        nom_cotisation = columns.TextColumn("Nom", sources=['type_cotisation__nom', 'unite_cotisation__nom'], processor='Get_nom_cotisation')
        depot = columns.TextColumn("Dépôt", sources=['depot_cotisation__date'], processor='Get_date_depot')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', 'idcotisation', 'date_debut', 'date_fin', 'famille', 'individu', 'nom_cotisation', 'numero', 'depot']
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            labels = {
                "date_debut": "Début",
                "date_fin": "Fin",
            }
            ordering = ["date_debut"]

        def Get_nom_cotisation(self, instance, *args, **kwargs):
            if instance.prestation:
                return instance.prestation.label
            else:
                return "%s - %s" % (instance.type_cotisation.nom, instance.unite_cotisation.nom)

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idindividu dans les boutons d'actions """
            html = [
                self.Create_bouton_imprimer(url=reverse("famille_voir_cotisation", kwargs={"idfamille": instance.famille_id, "idcotisation": instance.pk}), title="Imprimer ou envoyer par email l'adhésion"),
            ]
            return self.Create_boutons_actions(html)

        def Get_date_depot(self, instance, *args, **kwargs):
            if instance.depot_cotisation:
                return utils_dates.ConvertDateToFR(instance.depot_cotisation.date)
            return ""
