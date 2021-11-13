# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views import crud
from core.models import Vaccin
from portail.forms.individu_vaccinations import Formulaire
from portail.views.fiche import Onglet
from django.views.generic import TemplateView
from individus.utils import utils_vaccinations


class Page(Onglet):
    model = Vaccin
    url_liste = "portail_individu_vaccinations"
    url_ajouter = "portail_individu_vaccinations_ajouter"
    url_modifier = "portail_individu_vaccinations_modifier"
    url_supprimer = "portail_individu_vaccinations_supprimer"
    description_liste = "Cliquez sur le bouton Ajouter au bas de la page pour ajouter une nouvelle vaccination."
    description_saisie = "Saisissez les informations concernant la vaccination et cliquez sur le bouton Enregistrer."
    objet_singulier = "une vaccination"
    objet_pluriel = "des vaccinations"
    onglet_actif = "individu_vaccinations"
    categorie = "individu_vaccinations"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['onglet_actif'] = self.onglet_actif
        if not self.get_dict_onglet_actif().validation_auto:
            context['box_introduction'] = self.description_saisie + " Ces informations devront être validées par l'administrateur de l'application."
        return context

    def get_object(self):
        if not self.kwargs.get("idvaccin"):
            return None
        return Vaccin.objects.get(pk=self.kwargs.get("idvaccin"))

    def get_success_url(self):
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idrattachement': self.kwargs['idrattachement']})


class Liste(Page, TemplateView):
    model = Vaccin
    template_name = "portail/individu_vaccinations.html"

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['box_titre'] = "Vaccinations"
        context['box_introduction'] = "Cliquez sur le bouton Ajouter au bas de la page pour ajouter une nouvelle vaccination."
        context['liste_vaccinations'] = Vaccin.objects.select_related("type_vaccin").filter(individu=self.get_rattachement().individu).order_by("date")
        context['vaccins_obligatoires'] = utils_vaccinations.Get_vaccins_obligatoires_individu(individu=self.get_rattachement().individu)
        return context


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "portail/fiche_edit.html"

class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "portail/fiche_edit.html"

class Supprimer(Page, crud.Supprimer):
    template_name = "portail/fiche_delete.html"
