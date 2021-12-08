# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views import crud
from fiche_famille.views.famille import Onglet
from core.models import PortailMessage, Structure
from outils.forms.messagerie_portail import Formulaire, Envoi_notification_message
from django.db.models import Q, Count


class Page(Onglet):
    model = PortailMessage

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['onglet_actif'] = "outils"

        # Importation de toutes les structures
        context['liste_structures'] = Structure.objects.filter(pk__in=self.request.user.structures.all()).order_by("nom")

        # Importation du nombre de messages non lus (regroupement par structure)
        context['dict_messages_par_structure'] = {valeur["structure"]: valeur["nbre"] for valeur in PortailMessage.objects.values("structure").filter(famille_id=self.Get_idfamille()).annotate(nbre=Count('pk'))}

        # Discussion sélectionnée
        liste_messages_discussion = PortailMessage.objects.select_related("structure", "utilisateur").filter(famille_id=self.Get_idfamille(), structure_id=self.get_idstructure()).order_by("date_creation")
        context['liste_messages_discussion'] = list(liste_messages_discussion)

        # Importation de la structure
        if self.get_idstructure():
            context["structure"] = Structure.objects.get(pk=self.get_idstructure())

        return context

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idstructure"] = self.get_idstructure()
        form_kwargs["idfamille"] = self.Get_idfamille()
        return form_kwargs

    def get_idstructure(self):
        return self.kwargs.get("idstructure", 0)

    def get_success_url(self):
        return reverse_lazy("famille_messagerie_portail", kwargs={'idstructure': self.get_idstructure(), 'idfamille': self.Get_idfamille()})


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "fiche_famille/famille_messagerie_portail.html"
    texte_confirmation = "Le message a bien été envoyé"

    def form_valid(self, form):
        """ Envoie une notification de nouveau message à la famille par email """
        Envoi_notification_message(request=self.request, famille=form.cleaned_data["famille"], structure=form.cleaned_data["structure"])
        return super(Ajouter, self).form_valid(form)
