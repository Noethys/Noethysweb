# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from portail.views.base import CustomView
from django.views.generic import TemplateView
from django.utils.translation import gettext as _
from individus.utils import utils_pieces_manquantes
from portail.utils import utils_approbations
from core.models import PortailDocument
from core.utils import utils_dates


class View(CustomView, TemplateView):
    menu_code = "portail_documents"
    template_name = "portail/documents.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = _("Documents")

        # Pièces à fournir
        context['pieces_fournir'] = utils_pieces_manquantes.Get_pieces_manquantes(famille=self.request.user.famille, exclure_individus=self.request.user.famille.individus_masques.all())

        # Importation des documents à télécharger
        liste_documents = []
        for document in PortailDocument.objects.all().order_by("titre"):
            liste_documents.append({"titre": document.titre, "texte": document.texte, "fichier": document.document, "couleur_fond": document.couleur_fond, "extension": document.Get_extension()})
        for unite_consentement in utils_approbations.Get_approbations_requises(famille=self.request.user.famille, avec_consentements_existants=False).get("consentements", []):
            if unite_consentement.document.name:
                liste_documents.append({"titre": unite_consentement.type_consentement.nom, "texte": "Version du %s" % utils_dates.ConvertDateToFR(unite_consentement.date_debut), "fichier": unite_consentement.document, "couleur_fond": "primary", "extension": unite_consentement.Get_extension()})
        context['liste_documents'] = liste_documents

        return context
