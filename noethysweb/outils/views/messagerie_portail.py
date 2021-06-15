# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy
from core.views import crud
from core.models import PortailMessage, Structure, Famille
from outils.forms.messagerie_portail import Formulaire
from django.template.defaultfilters import truncatechars, striptags


class Page(crud.Page):
    model = PortailMessage
    menu_code = "messagerie"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['page_titre'] = "Messagerie"
        liste_messages_discussion = PortailMessage.objects.select_related("famille", "structure", "utilisateur").filter(famille_id=self.get_idfamille(), structure_id=self.get_idstructure()).order_by("date_creation")
        context['liste_messages_discussion'] = list(liste_messages_discussion)
        context['messagerie_liste_messages_non_lus'] = list(PortailMessage.objects.select_related("famille", "structure").filter(utilisateur__isnull=True, date_lecture__isnull=True))

        if self.get_idstructure():
            context["structure"] = Structure.objects.get(pk=self.get_idstructure())
        if self.get_idfamille():
            context["famille"] = Famille.objects.get(pk=self.get_idfamille())

        # Indiquer que les messages de la discussion ouverte sont lus
        if liste_messages_discussion:
            liste_messages_discussion.update(date_lecture=datetime.datetime.now())

        return context

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idstructure"] = self.get_idstructure()
        form_kwargs["idfamille"] = self.get_idfamille()
        return form_kwargs

    def get_idfamille(self):
        return self.kwargs.get("idfamille", 0)

    def get_idstructure(self):
        return self.kwargs.get("idstructure", 0)

    def get_success_url(self):
        return reverse_lazy("messagerie_portail", kwargs={'idstructure': self.get_idstructure(), 'idfamille': self.get_idfamille()})


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "outils/messagerie_portail.html"
    texte_confirmation = "Le message a bien été envoyé"
    titre_historique = "Ajouter un message"

    def Get_detail_historique(self, instance):
        return "Texte=%s" % (truncatechars(striptags(instance.texte), 40))
