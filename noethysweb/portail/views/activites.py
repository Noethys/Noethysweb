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


class View(CustomView, TemplateView):
    menu_code = "portail_activites"
    template_name = "portail/activites.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = _("Activités")

        # Importation des inscriptions
        conditions = Q(famille=self.request.user.famille) & Q(statut="ok") & (Q(date_fin__isnull=True) | Q(date_fin__gte=datetime.date.today())) & Q(individu__deces=False)
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
        for demande in PortailRenseignement.objects.select_related("individu").filter(famille=self.request.user.famille, etat="ATTENTE", code="inscrire_activite").order_by("individu__prenom"):
            demande.nom_activite = dict_activites.get(int(json.loads(demande.nouvelle_valeur).split(";")[0]), "?")
            demandes.append(demande)
        context["demandes_inscriptions_attente"] = demandes

        # Vérifie si des activités sont ouvertes à l'inscription
        context["activites_ouvertes_inscription"] = Activite.objects.filter((Q(portail_inscriptions_affichage="TOUJOURS") | (Q(portail_inscriptions_affichage="PERIODE") & Q(portail_inscriptions_date_debut__lte=datetime.datetime.now()) & Q(portail_inscriptions_date_fin__gte=datetime.datetime.now())))).exists()

        return context
