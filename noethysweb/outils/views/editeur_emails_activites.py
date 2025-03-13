# -*- coding: utf-8 -*-
#  Copyright (c) 2025 Faouzia TEKAYA.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from django.db.models import Count, F
from core.models import Mail, DocumentJoint, Inscription, Destinataire, Activite
from django.http import JsonResponse
from django.contrib import messages
import json
def Transferer_activites(request):
    if request.method != "POST":
        return JsonResponse({"erreur": "Méthode invalide."}, status=405)

    data = json.loads(request.POST.get("activites_selectionnees", "[]"))
    if not data:
        return JsonResponse({"erreur": "Aucune activité sélectionnée."}, status=401)

    # Créer le Mail
    mail = Mail.objects.create(
        categorie="activites",
        objet="Informations sur l'activité",
        html="",
        adresse_exp=request.user.Get_adresse_exp_defaut(),
        selection="NON_ENVOYE",
        verrouillage_destinataires=False,
        utilisateur=request.user,
    )

    # Trouver toutes les familles ayant une inscription pour ces activités
    inscriptions = (
        Inscription.objects
        .filter(activite_id__in=data, famille__isnull=False)
        .select_related("famille")
    )

    # Ajouter un Destinataire par famille
    familles_dict = {}
    for insc in inscriptions:
        if insc.famille and insc.famille.mail:
            familles_dict[insc.famille.pk] = insc.famille.mail

    liste_anomalies = []
    for fam_id, email in familles_dict.items():
        if email:
            destinataire = Destinataire.objects.create(
                categorie="activites",
                famille_id=fam_id,
                adresse=email,
            )
            mail.destinataires.add(destinataire)
        else:
            # Facultatif : signaler l'absence d'email
            liste_anomalies.append(str(fam_id))

    if liste_anomalies:
        messages.error(
            request,
            "Familles sans email : %s" % ", ".join(liste_anomalies)
        )

    # Retourne l’URL pour l’ouvrir dans l’éditeur d’emails
    url = reverse_lazy("editeur_emails", kwargs={"pk": mail.pk})
    return JsonResponse({"url": url})

def Impression_pdf(request):
    # Récupération des activites cochées
    activites_cochees = json.loads(request.POST.get("activites_cochees"))
    if not activites_cochees:
        return JsonResponse({"erreur": "Veuillez cocher au moins une activité dans la liste"}, status=401)

    # Création des PDF
    from fiche_individu.utils import utils_activites
    activite = utils_activites.Activites()
    resultat = activite.Impression(liste_activites=activites_cochees, dict_options={},mode_email=True)  # Mise à jour du paramètre
    if not resultat:
        return JsonResponse({"success": False}, status=401)

    # Création du mail
    logger.debug("Création d'un nouveau mail...")
    mail = Mail.objects.create(
        categorie="activites",
        objet="Notification d'activité",
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
        inscriptions = Inscription.objects.select_related('famille').filter(activite_id=IDcotisation)

        for cotisation in inscriptions:
            if cotisation.famille.mail:
                destinataire = Destinataire.objects.create(categorie="famille", famille=cotisation.famille,adresse=cotisation.famille.mail)
                document_joint = DocumentJoint.objects.create(nom="Activite", fichier=donnees["nom_fichier"])
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
    model = Activite
    url_liste = "editeur_emails_activites"
    menu_code = "editeur_emails_activites"

from outils.views.editeur_emails import Page_destinataires
class Liste(Page_destinataires, crud.Liste):
    template_name = "outils/editeur_emails_activites.html"
    model = Activite
    categorie = "activites"

    def get_queryset(self):
        queryset = (
            Inscription.objects
            .filter(famille__mail__isnull=False)
            .annotate(
                id_activite=F("activite__idactivite"),  # <-- ADDED
                nom_activite=F("activite__nom"),
                nom_groupe=F("groupe__nom"),
            )
            .values("id_activite", "nom_activite", "nom_groupe")
            .annotate(nombre_inscriptions=Count("idinscription"))
            .order_by("nom_activite", "nom_groupe")
        )
        return queryset

    def get_context_data(self, **kwargs):

        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Envoi des Inscrits aux Activites par Email"
        context['box_titre'] = "Envoyer des Inscrits aux Activites par Email en lot"
        context['box_introduction'] = "Cochez les activites puis cliquez sur le bouton Aperçu."
        context['onglet_actif'] = "activites_email"
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        return context

    class datatable_class(MyDatatable):
        filtres = ['id_activite','activite__nom', 'groupe__nom', 'nombre_inscriptions']
        model = None
        check = columns.CheckBoxSelectColumn(label="")
        c_activite_id = columns.TextColumn("Activité", sources=["id_activite"])

        c_activite = columns.TextColumn("Activité", sources=["nom_activite"])
        c_groupes = columns.TextColumn("Groupes", sources=["nom_groupe"])
        c_nb = columns.TextColumn("Nombre d'inscriptions", sources=["nombre_inscriptions"])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check","c_activite_id" ,"c_activite", "c_groupes", "c_nb"]

        def get_object_pk(self, row):
            # Return the real integer ID
            row=row["id_activite"]
            return row

        def prepare_results(self, queryset):
            results = []
            for row in queryset:
                results.append({
                    "id_activite": row["id_activite"],
                    "nom_activite": row["nom_activite"],
                    "nom_groupe": row["nom_groupe"],
                    "nombre_inscriptions": row["nombre_inscriptions"],
                })
            return results

        def Formate_statut(self, instance, *args, **kwargs):
            if instance.statut == "attente":
                return "<i class='fa fa-hourglass-2 text-yellow'></i> Attente"
            elif instance.statut == "refus":
                return "<i class='fa fa-times-circle text-red'></i> Refus"
            else:
                return "<i class='fa fa-check-circle-o text-green'></i> Valide"