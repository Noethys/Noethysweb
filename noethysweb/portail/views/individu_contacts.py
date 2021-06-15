# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views import crud
from core.models import PortailRenseignement, ContactUrgence
from portail.forms.individu_contacts import Formulaire
from portail.views.fiche import Onglet, ConsulterBase
from django.views.generic import TemplateView


class Page(Onglet):
    model = ContactUrgence
    url_liste = "portail_individu_contacts"
    url_ajouter = "portail_individu_contacts_ajouter"
    url_modifier = "portail_individu_contacts_modifier"
    url_supprimer = "portail_individu_contacts_supprimer"
    description_liste = "Cliquez sur le bouton Ajouter au bas de la page pour ajouter un nouveau contact."
    description_saisie = "Saisissez les informations concernant le contact et cliquez sur le bouton Enregistrer."
    objet_singulier = "un contact d'urgence et de sortie"
    objet_pluriel = "des contacts d'urgence et de sortie"
    onglet_actif = "individu_contacts"
    categorie = "individu_contacts"


    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['onglet_actif'] = self.onglet_actif
        if not self.get_dict_onglet_actif().validation_auto:
            context['box_introduction'] = self.description_saisie + " Ces informations devront être validées par l'administrateur de l'application."
        return context

    def get_object(self):
        if not self.kwargs.get("idcontact"):
            return None
        return ContactUrgence.objects.get(pk=self.kwargs.get("idcontact"))

    def get_success_url(self):
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idrattachement': self.kwargs['idrattachement']})


class Liste(Page, TemplateView):
    model = ContactUrgence
    template_name = "portail/individu_contacts.html"

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['box_titre'] = "Contacts d'urgence et de sortie"
        context['box_introduction'] = "Cliquez sur le bouton Ajouter au bas de la page pour ajouter un nouveau contact."
        context['liste_contacts'] = ContactUrgence.objects.filter(famille=self.get_rattachement().famille, individu=self.get_rattachement().individu).order_by("nom", "prenom")
        return context


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "portail/fiche_edit.html"

class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "portail/fiche_edit.html"


class Supprimer(Page, crud.Supprimer):
    template_name = "portail/fiche_delete.html"
