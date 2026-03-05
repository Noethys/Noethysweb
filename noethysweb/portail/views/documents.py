# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.utils.translation import gettext as _
from django.views.generic import TemplateView

from portail.views.base import CustomView
from individus.utils import utils_pieces_manquantes
from portail.utils import utils_approbations
from core.models import PortailDocument, Inscription, Attestationdoc, Piece
from core.utils import utils_dates

logger = logging.getLogger(__name__)

class View(CustomView, TemplateView):
    menu_code = "portail_documents"
    template_name = "portail/documents.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = _("Documents")

        # Pièces à fournir
        context['pieces_fournir'] = utils_pieces_manquantes.Get_pieces_manquantes(
            famille=self.request.user.famille,
            exclure_individus=self.request.user.famille.individus_masques.all()
        )

        # Récupération des activités de la famille
        conditions = Q(famille=self.request.user.famille)
        inscriptions = Inscription.objects.select_related("activite", "individu").filter(conditions)
        activites = list({inscription.activite for inscription in inscriptions})

        # Importation des documents à télécharger
        liste_documents = []
        documents = PortailDocument.objects.filter(Q(activites__in=activites), activites__visible=True).order_by("titre").distinct()
        for document in documents:
            liste_documents.append({
                "titre": document.titre,
                "texte": document.texte,
                "fichier": document.document,
                "couleur_fond": document.couleur_fond,
                "extension": document.Get_extension()
            })
        for unite_consentement in utils_approbations.Get_approbations_requises(
                famille=self.request.user.famille,
                avec_consentements_existants=False
        ).get("consentements", []):
            liste_documents.append({
                "titre": unite_consentement.type_consentement.nom,
                "texte": "Version du %s" % utils_dates.ConvertDateToFR(unite_consentement.date_debut),
                "fichier": unite_consentement.document,
                "couleur_fond": "primary",
                "extension": unite_consentement.Get_extension()
            })
        context['liste_documents'] = liste_documents

        famille = self.request.user.famille
        # Récupérer les pièces de la famille ET des individus (pour gérer valide_rattachement)
        individus_famille = famille.rattachement_set.all().values_list('individu_id', flat=True)
        pieces = Piece.objects.filter(Q(famille=famille) | Q(individu__in=individus_famille))
        context['liste_pieces'] = pieces

        attestation = Attestationdoc.objects.filter(famille=famille)
        context['liste_attestations'] = attestation

        return context

def supprimer_piece(request, pk):
    piece = get_object_or_404(Piece, pk=pk)
    if request.method == 'POST':
        piece.delete()
        messages.success(request, 'La pièce a été supprimée avec succès.')
        return redirect('portail_documents')  # Redirigez vers la vue appropriée
    return render(request, 'core/confirmation_suppression.html', {'piece': piece})
