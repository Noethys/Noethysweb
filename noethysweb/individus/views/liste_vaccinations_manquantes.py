# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json, time
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q
from core.views import crud
from core.models import Activite, ModeleEmail, Mail, Destinataire, Famille, Inscription
from core.views.customdatatable import CustomDatatable, Colonne
from core.utils import utils_dates
from individus.utils import utils_vaccinations
from individus.forms.liste_vaccinations_manquantes import Formulaire


def Envoi_emails(request):
    time.sleep(1)

    # Récupération des attestations fiscales cochées
    lignes_cochees = json.loads(request.POST.get("lignes_cochees"))
    if not lignes_cochees:
        return JsonResponse({"erreur": "Veuillez cocher au moins une ligne dans la liste"}, status=401)

    # Création du mail
    logger.debug("Création d'un nouveau mail...")
    modele_email = ModeleEmail.objects.filter(categorie="rappel_vaccinations_manquantes", defaut=True).first()
    mail = Mail.objects.create(
        categorie="rappel_vaccinations_manquantes",
        objet=modele_email.objet if modele_email else "",
        html=modele_email.html if modele_email else "",
        adresse_exp=request.user.Get_adresse_exp_defaut(),
        selection="NON_ENVOYE",
        verrouillage_destinataires=True,
        utilisateur=request.user,
    )

    # Importation des familles
    dict_familles = {famille.pk: famille for famille in Famille.objects.filter(pk__in=[int(valeurs[1]) for valeurs in lignes_cochees])}

    # Création des destinataires et des documents joints
    logger.debug("Enregistrement des destinataires...")
    liste_anomalies = []
    for valeurs in lignes_cochees:
        famille = dict_familles[int(valeurs[1])]
        valeurs_fusion = {"{NOM_FAMILLE}": famille.nom, "{NOM_COMPLET_INDIVIDU}": valeurs[2], "{LISTE_VACCINATIONS_MANQUANTES}": valeurs[3]}
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
    menu_code = "liste_vaccinations_manquantes"


class Liste(Page, crud.CustomListe):
    template_name = "individus/liste_vaccinations_manquantes.html"

    filtres = ["fgenerique:idfamille", "famille", "igenerique:idindividu", "individu"]
    colonnes = [
        Colonne(code="check", label="check"),
        Colonne(code="idfamille", label="ID", classe="IntegerField"),
        Colonne(code="individu", label="Individu", classe="CharField", label_filtre="Individu"),
        Colonne(code="vaccinations", label="Vaccinations manquantes", classe="CharField", label_filtre="Vaccinations manquantes"),
        Colonne(code="famille", label="Famille", classe="CharField", label_filtre="Famille"),
    ]

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context["page_titre"] = "Liste des vaccinations manquantes"
        context["box_titre"] = "Liste des vaccinations manquantes"
        context["box_introduction"] = "Voici ci-dessous la liste des vaccinations manquantes."
        context["impression_introduction"] = ""
        context["impression_conclusion"] = ""
        context["hauteur_table"] = "400px"
        context["active_checkbox"] = True
        if "form_parametres" not in kwargs:
            context["form_parametres"] = Formulaire(request=self.request)
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
            masquer_activites_anciennes = parametres["masquer_activites_anciennes"]

            param_activites = json.loads(parametres["activites"])
            if param_activites["type"] == "groupes_activites":
                liste_activites = Activite.objects.filter(groupes_activites__in=param_activites["ids"])
            if param_activites["type"] == "activites":
                liste_activites = Activite.objects.filter(pk__in=param_activites["ids"])
            presents = utils_dates.ConvertDateRangePicker(parametres["presents"]) if parametres["presents"] else None

            # Importation des inscriptions
            conditions = Q(individu__deces=False)
            if liste_activites:
                conditions &= Q(activite__in=liste_activites) & (Q(date_fin__isnull=True) | Q(date_fin__gte=date_reference))
            if presents:
                conditions &= Q(consommation__date__gte=presents[0], consommation__date__lte=presents[1])
            if masquer_activites_anciennes:
                conditions &= (Q(activite__date_fin__isnull=True) | Q(activite__date_fin__gte=date_reference))
            inscriptions = Inscription.objects.select_related("individu", "famille").filter(conditions).distinct()

            # Importation des vaccinations manquantes
            dict_individus = utils_vaccinations.Get_vaccins_obligatoires_by_inscriptions(inscriptions=inscriptions)

            # Mise en forme des données
            lignes = []
            for (famille, individu), liste_maladies in dict_individus.items():
                lignes.append(["", famille.pk, individu.Get_nom(), ", ".join([dict_temp["label"] for dict_temp in liste_maladies if not dict_temp["valide"]]), famille.nom])

        return CustomDatatable(colonnes=self.colonnes, lignes=lignes, filtres=self.Get_filtres())
