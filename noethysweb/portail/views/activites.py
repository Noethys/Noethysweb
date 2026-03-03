# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime, json
logger = logging.getLogger(__name__)
from django.db.models import Q
from django.utils.translation import gettext as _
from django.views.generic import TemplateView
from core.models import Inscription, PortailRenseignement, Activite
from portail.views.base import CustomView
from portail.utils import utils_approbations
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse


def Appliquer_modification(request):
    iddemande = int(request.POST["iddemande"])
    etat = request.POST["etat"]
    demande = PortailRenseignement.objects.get(idrenseignement=iddemande)
    demande.delete()
    url_redirection = reverse('portail_activites')
    return JsonResponse({"redirection": url_redirection})

class View(CustomView, TemplateView):
    menu_code = "portail_activites"
    template_name = "portail/activites.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = _("Liste des inscriptions")

        approbations_requises = utils_approbations.Get_approbations_requises(famille=self.request.user.famille)
        context['nbre_approbations_requises'] = approbations_requises["nbre_total"]

        # Importation des inscriptions
        conditions = Q(famille=self.request.user.famille) & Q(statut="ok") & (Q(date_fin__isnull=True) | Q(date_fin__gte=datetime.date.today())) & Q(individu__deces=False) & Q(activite__actif=True)
        inscriptions = Inscription.objects.select_related("activite", "individu").filter(conditions).exclude(individu__in=self.request.user.famille.individus_masques.all())

        # Récupération des individus
        context['liste_individus'] = sorted(list(set([inscription.individu for inscription in inscriptions])), key=lambda individu: individu.prenom)

        # Récupération des activités pour chaque individu
        dict_inscriptions = {}
        for inscription in inscriptions:
            dict_inscriptions.setdefault(inscription.individu, [])
            dict_inscriptions[inscription.individu].append(inscription)
        for individu in context['liste_individus']:
            individu.inscriptions = sorted(dict_inscriptions[individu], key=lambda inscription: inscription.activite.nom)

        # Demandes d'inscription en attente de traitement
        demandes = []
        dict_activites = {activite.pk: activite.nom for activite in Activite.objects.all()}
        for demande in PortailRenseignement.objects.select_related("individu").filter(famille=self.request.user.famille,
                                                                                      etat="ATTENTE",
                                                                                      code="inscrire_activite").order_by("individu__prenom"):
            try:
                # Tentative de décodage JSON
                nouvelle_valeur = demande.nouvelle_valeur
                nouvelle_valeur_json = json.loads(nouvelle_valeur)
                activite_id = nouvelle_valeur_json.split(";")[
                    0]  # En supposant que nouvelle_valeur_json est une chaîne de caractères
                demande.nom_activite = dict_activites.get(int(activite_id), "?")
            except (json.JSONDecodeError, ValueError) as e:
                # Gestion des erreurs de décodage JSON
                print(f"Erreur lors du décodage JSON pour la demande {demande.idrenseignement}: {e}")
                demande.nom_activite = "?"  # ou traitez-la d'une manière qui convient à votre application
            demandes.append(demande)

        context["demandes_inscriptions_attente"] = demandes

        # Vérifie si des activités sont ouvertes à l'inscription
        context["activites_ouvertes_inscription"] = Activite.objects.filter((Q(visible=True) & Q(portail_inscriptions_affichage="TOUJOURS") | (Q(portail_inscriptions_affichage="PERIODE") & Q(portail_inscriptions_date_debut__lte=datetime.datetime.now()) & Q(portail_inscriptions_date_fin__gte=datetime.datetime.now())))).exists()
        inscriptions = Inscription.objects.filter(famille=self.request.user.famille, besoin_certification=True)
        context["nbre_verifications_manquantes"] = inscriptions.count()
        return context

