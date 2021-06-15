# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views import crud
from core.models import PortailRenseignement, ProblemeSante
from portail.forms.individu_infos_medicales import Formulaire
from portail.views.fiche import Onglet, ConsulterBase
from django.views.generic import TemplateView


class Page(Onglet):
    model = ProblemeSante
    url_liste = "portail_individu_infos_medicales"
    url_ajouter = "portail_individu_infos_medicales_ajouter"
    url_modifier = "portail_individu_infos_medicales_modifier"
    url_supprimer = "portail_individu_infos_medicales_supprimer"
    description_liste = "Cliquez sur le bouton Ajouter au bas de la page pour ajouter une nouvelle information."
    description_saisie = "Saisissez les informations nécessaires et cliquez sur le bouton Enregistrer."
    objet_singulier = "une information médicale"
    objet_pluriel = "des informations médicales"
    onglet_actif = "individu_infos_medicales"
    categorie = "individu_infos_medicales"


    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['onglet_actif'] = self.onglet_actif
        if not self.get_dict_onglet_actif().validation_auto:
            context['box_introduction'] = self.description_saisie + " Ces informations devront être validées par l'administrateur de l'application."
        return context

    def get_object(self):
        if not self.kwargs.get("idprobleme"):
            return None
        return ProblemeSante.objects.get(pk=self.kwargs.get("idprobleme"))

    def get_success_url(self):
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idrattachement': self.kwargs['idrattachement']})


class Liste(Page, TemplateView):
    model = ProblemeSante
    template_name = "portail/individu_infos_medicales.html"

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['box_titre'] = "Informations médicales"
        context['box_introduction'] = "Cliquez sur le bouton Ajouter au bas de la page pour ajouter une nouvelle information."
        context['liste_informations'] = ProblemeSante.objects.filter(individu=self.get_rattachement().individu).order_by("intitule")
        return context


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "portail/fiche_edit.html"


class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "portail/fiche_edit.html"


class Supprimer(Page, crud.Supprimer):
    template_name = "portail/fiche_delete.html"
