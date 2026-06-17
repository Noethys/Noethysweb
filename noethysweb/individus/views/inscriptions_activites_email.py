# -*- coding: utf-8 -*-
#  Copyright (c) 2025 Faouzia TEKAYA.
#  Copyright (c) 2026 Abderrahmane RHIABI - GIP RECIA.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

# Adapté depuis outils/views/editeur_emails_activites.py (Faouzia, branche emails-par-lot)
# Déplacé dans individus/ par cohérence avec inscriptions_email.py (convention Ivan)
# Permet d'envoyer un email groupé à toutes les familles d'une activité sélectionnée.

import logging
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from django.db.models import Count, F 
from core.models import Mail, DocumentJoint, Inscription, Destinataire, Activite
from django.http import JsonResponse
from django.contrib import messages
import json


# cette methode est appelée par un appel AJAX depuis la page de liste des activités (inscriptions_activites_email)
# lorsque l'utilisateur clique sur le bouton "Transférer" après avoir coché les activités qu'il souhaite envoyer par email.
# elle génère un PDF par activité avec les familles inscrites, crée un mail groupé avec les champs de fusion correspondants, et redirige vers l'éditeur d'emails.
def Impression_pdf(request):
    # Récupération des activités cochées
    activites_cochees = json.loads(request.POST.get("activites_cochees"))
    if not activites_cochees:
        return JsonResponse({"erreur": "Veuillez cocher au moins une activité dans la liste"}, status=401)

    # utils_activites.py pour récupérer les données d'impression, utils_impression_activites.py pour générer les PDF
    from fiche_individu.utils import utils_activites
    activite = utils_activites.Activites()
    resultat = activite.Impression(liste_activites=activites_cochees, dict_options={}, mode_email=True)
    if not resultat:
        return JsonResponse({"success": False}, status=401)

    # Utilise le modèle email par défaut de catégorie "activites" si disponible
    from core.models import ModeleEmail
    modele_email = ModeleEmail.objects.filter(categorie="activites", defaut=True).first()
    mail = Mail.objects.create(
        categorie="activites",
        objet=modele_email.objet if modele_email else "Notification d'activité",
        html=modele_email.html if modele_email else "",
        adresse_exp=request.user.Get_adresse_exp_defaut(),
        selection="NON_ENVOYE",
        verrouillage_destinataires=True,
        utilisateur=request.user,
    )

    # 1 destinataire par inscription (par enfant)
    liste_anomalies = []
    for IDinscription, donnees in resultat["noms_fichiers"].items():
        cotisation = Inscription.objects.select_related('famille').get(pk=IDinscription)
        if cotisation.famille.mail:
            destinataire = Destinataire.objects.create(
                categorie="activites",
                famille=cotisation.famille,
                adresse=cotisation.famille.mail,
                valeurs=json.dumps(donnees["valeurs"])
            )
            document_joint = DocumentJoint.objects.create(nom="Activite", fichier=donnees["nom_fichier"])
            destinataire.documents.add(document_joint)
            mail.destinataires.add(destinataire)
        else:
            liste_anomalies.append(cotisation.famille.nom)

    if liste_anomalies:
        messages.add_message(request, messages.ERROR, "Adresses mail manquantes : %s" % ", ".join(liste_anomalies))

    url = reverse_lazy("editeur_emails", kwargs={'pk': mail.pk})
    return JsonResponse({"url": url})


class Page(crud.Page):
    model = Activite
    url_liste = "inscriptions_activites_email"
    menu_code = "inscriptions_activites_email"


class Liste(Page, crud.Liste):
    template_name = "individus/inscriptions_activites_email.html"
    model = Activite
    categorie = "activites"

    def get_queryset(self):
        queryset = (
            Inscription.objects
            .filter(famille__mail__isnull=False,
                    activite__structure__in=self.request.user.structures.all()
            )
            .annotate(
                id_activite=F("activite__idactivite"),
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
        context['page_titre'] = "Envoi des Inscrits aux Activités par Email"
        context['box_titre'] = "Envoyer des Inscrits aux Activités par Email en lot"
        context['box_introduction'] = "Cochez les activités puis cliquez sur le bouton Transférer."
        context['onglet_actif'] = "inscriptions_activites_email" 
        context['active_checkbox'] = True # dit au template d'afficher les cases à cocher sur chaque ligne du tableau.
        context['bouton_supprimer'] = False # dit au template de cacher le bouton "Supprimer" — on ne veut pas supprimer des activités depuis cette page.
        return context

    # c'est la définition du tableau affiché sur la page. 
    class datatable_class(MyDatatable):
        filtres = ['id_activite', 'activite__nom', 'groupe__nom', 'nombre_inscriptions']
        model = None
        check = columns.CheckBoxSelectColumn(label="")
        c_activite_id = columns.TextColumn("ID Activité", sources=["id_activite"])
        c_activite = columns.TextColumn("Activité", sources=["nom_activite"])
        c_groupes = columns.TextColumn("Groupes", sources=["nom_groupe"])
        c_nb = columns.TextColumn("Nombre d'inscriptions", sources=["nombre_inscriptions"])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "c_activite_id", "c_activite", "c_groupes", "c_nb"]

        def get_object_pk(self, row):
            return row["id_activite"]

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
        
