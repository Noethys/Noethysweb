# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime, json
from django.http import Http404
from core.models import Rattachement
from django.db.models import Q
from django.utils.translation import gettext as _
from django.views.generic import TemplateView
from core.models import Inscription, PortailRenseignement, Activite
from portail.views.base import CustomView
logger = logging.getLogger(__name__)


class View(CustomView, TemplateView):
    menu_code = "portail_activites"
    template_name = "portail/activites.html"

    def get_object(self):
        """Récupérer l'objet famille ou individu selon l'utilisateur"""
        if hasattr(self.request.user, 'famille'):
            return self.request.user.famille
        elif hasattr(self.request.user, 'individu'):
            return self.request.user.individu
        else:
            raise Http404("Utilisateur non reconnu.")

    def get_famille_object(self):
        """Récupérer les familles de l'individu si applicable"""
        if hasattr(self.request.user, 'famille'):
            return [self.request.user.famille]
        elif hasattr(self.request.user, 'individu'):
            rattachements = Rattachement.objects.filter(individu=self.request.user.individu)
            familles = [rattachement.famille for rattachement in rattachements if rattachement.famille and rattachement.titulaire == 1]
            return familles if familles else None
        return None

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = _("Activités")
        familles = self.get_famille_object()

        if familles:
            inscriptions = Inscription.objects.none()
            dict_famille_individus = {}
            dict_inscriptions = {}
            demandes = []
            dict_activites = {activite.pk: activite.nom for activite in Activite.objects.all()}

            for famille in familles:
                # Importation des inscriptions pour chaque famille
                conditions = Q(famille=famille) & Q(statut="ok") & (
                        Q(date_fin__isnull=True) | Q(date_fin__gte=datetime.date.today())) & Q(
                    individu__deces=False)
                inscriptions_famille = Inscription.objects.select_related("activite", "individu").filter(
                    conditions).exclude(individu__in=famille.individus_masques.all())
                inscriptions = inscriptions.union(inscriptions_famille)

                # Récupération des individus par famille
                individus_famille = sorted(
                    set(inscription.individu for inscription in inscriptions_famille),
                    key=lambda individu: individu.prenom
                )
                dict_famille_individus[famille] = individus_famille
                # Demandes d'inscription en attente de traitement pour chaque famille
                demandes_famille = PortailRenseignement.objects.select_related("individu").filter(
                    famille=famille, etat="ATTENTE", code="inscrire_activite"
                ).order_by("individu__prenom")

                for demande in demandes_famille:
                    try:
                        # Séparer la chaîne en fonction du point-virgule
                        nouvelle_valeur_parts = demande.nouvelle_valeur.split(";")

                        # Nettoyer les guillemets et récupérer l'ID de l'activité depuis la première partie
                        activite_id = int(nouvelle_valeur_parts[0].strip('"'))

                    except (ValueError, IndexError) as e:
                        # Gérer les erreurs de conversion ou d'index manquant
                        print(
                            f"Erreur lors de l'extraction de l'activité pour la demande {demande.idrenseignement}: {e}")
                        activite_id = None

                    # Affecter le nom de l'activité à partir de l'ID récupéré ou une valeur par défaut "?"
                    demande.nom_activite = dict_activites.get(activite_id, "?")
                    demandes.append(demande)

                # Récupération des inscriptions pour chaque individu
                for inscription in inscriptions_famille:
                    dict_inscriptions.setdefault(inscription.individu, [])
                    dict_inscriptions[inscription.individu].append(inscription)

            # Trier les individus par famille, puis par prénom
            context['famille_individus'] = sorted(
                dict_famille_individus.items(),
                key=lambda item: item[0].nom  # Trier d'abord par le nom de la famille
            )
            # Ajouter les inscriptions triées pour chaque individu
            for famille, individus in context['famille_individus']:
                for individu in individus:
                    individu.inscriptions = sorted(dict_inscriptions[individu],
                                                   key=lambda inscription: inscription.activite.nom)

            # Ajouter les demandes d'inscription en attente
            context["demandes_inscriptions_attente"] = demandes
            # Vérifie si des activités sont ouvertes à l'inscription
            context["activites_ouvertes_inscription"] = Activite.objects.filter(
                (Q(portail_inscriptions_affichage="TOUJOURS") |
                 (Q(portail_inscriptions_affichage="PERIODE") &
                  Q(portail_inscriptions_date_debut__lte=datetime.datetime.now()) &
                  Q(portail_inscriptions_date_fin__gte=datetime.datetime.now())))
            ).exists()

        return context