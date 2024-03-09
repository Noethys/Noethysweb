# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json, time
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.contrib import messages
from core.views import crud
from core.models import Activite, ModeleEmail, Mail, Destinataire, Famille
from core.views.customdatatable import CustomDatatable, Colonne
from core.utils import utils_dates
from individus.utils import utils_pieces_manquantes
from individus.forms.liste_pieces_manquantes import Formulaire


def Envoi_emails(request):
    time.sleep(1)

    # Récupération des attestations fiscales cochées
    pieces_manquantes = json.loads(request.POST.get("familles_coches"))
    if not pieces_manquantes:
        return JsonResponse({"erreur": "Veuillez cocher au moins une ligne dans la liste"}, status=401)

    # Création du mail
    logger.debug("Création d'un nouveau mail...")
    modele_email = ModeleEmail.objects.filter(categorie="rappel_pieces_manquantes", defaut=True).first()
    mail = Mail.objects.create(
        categorie="rappel_pieces_manquantes",
        objet=modele_email.objet if modele_email else "",
        html=modele_email.html if modele_email else "",
        adresse_exp=request.user.Get_adresse_exp_defaut(),
        selection="NON_ENVOYE",
        verrouillage_destinataires=True,
        utilisateur=request.user,
    )

    # Importation des familles
    dict_familles = {famille.pk: famille for famille in Famille.objects.filter(pk__in=[valeurs[0] for valeurs in pieces_manquantes])}

    # Création des destinataires et des documents joints
    logger.debug("Enregistrement des destinataires...")
    liste_anomalies = []
    for idfamille, texte_pieces_manquantes in pieces_manquantes:
        famille = dict_familles[idfamille]
        valeurs_fusion = {"{NOM_FAMILLE}": famille.nom, "{LISTE_PIECES_MANQUANTES}": texte_pieces_manquantes}
        if famille.mail:
            destinataire = Destinataire.objects.create(categorie="famille", famille=famille, adresse=famille.mail, valeurs=json.dumps(valeurs_fusion))
            mail.destinataires.add(destinataire)
        else:
            liste_anomalies.append(famille.nom)

    if liste_anomalies:
        messages.add_message(request, messages.ERROR, "Adresses mail manquantes : %s" % ", ".join(liste_anomalies))

    # Création de l'URL pour ouvrir l'éditeur d'emails
    logger.debug("Redirection vers l'éditeur d'emails...")
    url = reverse_lazy("editeur_emails", kwargs={'pk': mail.pk})
    return JsonResponse({"url": url})


class Page(crud.Page):
    menu_code = "liste_pieces_manquantes"


class Liste(Page, crud.CustomListe):
    template_name = "individus/liste_pieces_manquantes.html"

    filtres = ["fgenerique:idfamille", "famille"]
    colonnes = [
        Colonne(code="check", label="check"),
        Colonne(code="idfamille", label="ID", classe="IntegerField"),
        Colonne(code="famille", label="Famille", classe="CharField", label_filtre="Famille"),
        Colonne(code="pieces", label="Pièces manquantes", classe="CharField", label_filtre="Pièces manquantes"),
    ]

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Liste des pièces manquantes"
        context['box_titre'] = "Liste des pièces manquantes"
        context['box_introduction'] = "Voici ci-dessous la liste des pièces manquantes."
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context["hauteur_table"] = "400px"
        context['active_checkbox'] = True
        if "form_parametres" not in kwargs:
            context['form_parametres'] = Formulaire(request=self.request)
            context["datatable"] = self.Get_customdatatable()
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if form.is_valid() == False:
            return self.render_to_response(self.get_context_data(form_parametres=form))
        context = {
            "form_parametres": form,
            "datatable": self.Get_customdatatable(parametres=form.cleaned_data)
        }
        return self.render_to_response(self.get_context_data(**context))

    def Get_customdatatable(self, parametres={}):
        lignes = []

        if parametres:
            # Récupération des paramètres
            date_reference = parametres["date"]
            masquer_complets = parametres["masquer_complets"]
            masquer_activites_anciennes = parametres["masquer_activites_anciennes"]

            param_activites = json.loads(parametres["activites"])
            if param_activites["type"] == "groupes_activites":
                liste_activites = Activite.objects.filter(groupes_activites__in=param_activites["ids"])
            if param_activites["type"] == "activites":
                liste_activites = Activite.objects.filter(pk__in=param_activites["ids"])

            if parametres["presents"]:
                date_min = utils_dates.ConvertDateENGtoDate(parametres["presents"].split(";")[0])
                date_max = utils_dates.ConvertDateENGtoDate(parametres["presents"].split(";")[1])
                presents = (date_min, date_max)
            else:
                presents = None

            # Importation des pièces manquantes
            dictPieces = utils_pieces_manquantes.Get_liste_pieces_manquantes(date_reference=date_reference, activites=liste_activites, presents=presents, only_concernes=masquer_complets, masquer_activites_anciennes=masquer_activites_anciennes)

            # Mise en forme des données
            lignes = []
            for idfamille, valeurs in dictPieces.items():
                lignes.append(["", idfamille, valeurs["nom_famille"], valeurs["texte"]])

        return CustomDatatable(colonnes=self.colonnes, lignes=lignes, filtres=self.Get_filtres())

