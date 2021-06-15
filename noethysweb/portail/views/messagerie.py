# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy
from core.views import crud
from core.models import PortailMessage, Structure
from portail.forms.messagerie import Formulaire
from portail.views.base import CustomView
from django.template.defaultfilters import truncatechars, striptags


class Page(CustomView):
    model = PortailMessage
    menu_code = "portail_contact"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['page_titre'] = "Messagerie"
        context['structure'] = Structure.objects.get(pk=self.get_idstructure())
        context['liste_messages'] = PortailMessage.objects.select_related("famille", "utilisateur").filter(famille=self.request.user.famille, structure_id=self.get_idstructure()).order_by("date_creation")

        # Importation des messages non lus
        liste_messages_non_lus = PortailMessage.objects.select_related("famille").filter(famille=self.request.user.famille, structure_id=self.get_idstructure(), utilisateur__isnull=False, date_lecture__isnull=True)
        context['liste_messages_non_lus'] = list(liste_messages_non_lus)

        # Enregistre la date de lecture pour les messages non lus
        liste_messages_non_lus.update(date_lecture=datetime.datetime.now())
        return context

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idstructure"] = self.get_idstructure()
        return form_kwargs

    def get_idstructure(self):
        return self.kwargs.get("idstructure", 0)

    def get_success_url(self):
        return reverse_lazy("portail_messagerie", kwargs={'idstructure': self.get_idstructure()})


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "portail/messagerie.html"
    texte_confirmation = "Le message a bien été envoyé"
    titre_historique = "Ajouter un message"

    def Get_detail_historique(self, instance):
        return "Destinataire=%s Texte=%s" % (instance.structure, truncatechars(striptags(instance.texte), 40))
