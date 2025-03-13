# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
from django.http import Http404
from core.models import Rattachement
logger = logging.getLogger(__name__)
from portail.views.base import CustomView
from django.views.generic import TemplateView
from django.utils.translation import gettext as _
from core.models import Structure, PortailMessage
from django.db.models import Q, Count


class View(CustomView, TemplateView):
    menu_code = "portail_contact"
    template_name = "portail/contact.html"
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
        context['page_titre'] = _("Contact")

        familles = self.get_famille_object()  # liste de familles liées à l'utilisateur

        if familles:
            # 1) Structures liées par au moins une inscription d’un individu de l’une des familles
            liste_structures = (
                Structure.objects
                .filter(
                    messagerie_active=True,
                    activite__inscription__famille__in=familles
                )
                .order_by("nom")
                .distinct()
            )

            # 2) Séparer celles qui ont la messagerie active
            context['liste_structures_messagerie'] = [
                s for s in liste_structures if s.messagerie_active
            ]

            # 3) Séparer celles qui affichent les coordonnées
            context['liste_structures_coords'] = [
                s for s in liste_structures if s.afficher_coords
            ]
            print("utilisateur=", self.request.user)
            # 4) Importation du nombre de messages non lus par structure
            #    pour toutes les familles (donc un filter(famille__in=familles)).
            qs_non_lus = (
                PortailMessage.objects
                .select_related("famille", "structure", "individu", "utilisateur")  # Charge en une seule requête
                .only("idmessage", "famille_id", "structure_id", "individu_id", "utilisateur_id", "texte",
                      "date_creation", "date_lecture")  # Charge seulement les colonnes nécessaires
                .values("structure")
                .filter(
                    Q(famille__in=familles),
                    Q(utilisateur__isnull=False),
                    Q(date_lecture__isnull=True),
                    # Ajouter la condition pour l'individu : pour filtrer les messages associés à l'individu de l'utilisateur connecté et les messages où l'individu est NULL (aucun individu associé).
                    Q(individu=self.request.user.individu) | Q(individu__isnull=True)
                )
                .exclude(utilisateur=self.request.user)
                .annotate(nbre=Count('pk'))
            )
            context['dict_messages_non_lus'] = {
                val["structure"]: val["nbre"] for val in qs_non_lus
            }

        return context
