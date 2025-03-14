# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json
from django.http import Http404, JsonResponse
from core.models import Rattachement
from core.models import Individu
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.translation import gettext_lazy as _
from core.views import crud
from core.models import PortailMessage, PortailRenseignement
from portail.forms.transmettre_piece import Formulaire
from portail.views.base import CustomView


def Get_individus(request):
    """Renvoie une liste d'individus pour la famille sélectionnée """
    famille_id = request.POST.get('famille')
    individus = Individu.objects.filter(rattachement__famille_id=famille_id)
    individu_options = [
        '<option value="{}">{}</option>'.format(individu.pk, individu.Get_nom()) for individu in individus
    ]
    return JsonResponse(''.join(individu_options), safe=False)


class Page(CustomView):
    model = PortailMessage
    menu_code = "portail_documents"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['page_titre'] = _("Transmettre un document")
        context['box_titre'] = None
        context['box_introduction'] = _("Renseignez les caractéristiques du document et cliquez sur le bouton Envoyer.")
        return context

    def get_success_url(self):
        return reverse_lazy("portail_documents")
    def get_object(self):
        """Récupérer l'objet famille ou individu selon l'utilisateur"""
        if hasattr(self.request.user, 'famille'):
            return self.request.user.famille
        elif hasattr(self.request.user, 'individu'):
            return self.request.user.individu
        else:
            raise Http404("Utilisateur non reconnu.")

    def get_famille_object(self):
        if hasattr(self.request.user, 'famille'):
            return self.request.user.famille
        elif hasattr(self.request.user, 'individu'):
            rattachement = Rattachement.objects.filter(individu=self.request.user.individu).first()
            if rattachement.famille and rattachement.titulaire == 1:
                return rattachement.famille
        return None


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    texte_confirmation = _("Le document a bien été transmis")
    titre_historique = _("Ajouter une pièce")
    template_name = "portail/edit.html"

    def Get_detail_historique(self, instance):
        famille = self.get_famille_object()
        return "Famille=%s, Pièce=%s" % (famille, instance.Get_nom())

    def Apres_form_valid(self, form=None, instance=None):
        # Mémorisation du renseignement
        famille = self.get_famille_object()
        PortailRenseignement.objects.create(famille=famille, individu=instance.individu,
                                            categorie="famille_pieces", code="Nouvelle pièce", validation_auto=True,
                                            nouvelle_valeur=json.dumps(instance.Get_nom(), cls=DjangoJSONEncoder), idobjet=instance.pk)
