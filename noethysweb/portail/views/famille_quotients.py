# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.urls import reverse_lazy
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from core.views import crud
from core.models import PortailRenseignement, Quotient
from portail.forms.famille_quotients import Formulaire
from portail.views.fiche import Onglet, ConsulterBase
from django.views.generic import TemplateView


class Page(Onglet):
    model = Quotient
    url_liste = "portail_famille_quotients"
    url_ajouter = "portail_famille_quotients_ajouter"
    url_modifier = "portail_famille_quotients_modifier"
    url_supprimer = "portail_famille_quotients_supprimer"
    description_liste = _("Cliquez sur le bouton Ajouter au bas de la page pour ajouter une nouveau quotient.")
    description_saisie = _("Saisissez les informations nécessaires et cliquez sur le bouton Enregistrer.")
    objet_singulier = _("un quotient familial")
    objet_pluriel = _("des quotients familiaux")
    onglet_actif = "famille_quotients"
    categorie = "famille_quotients"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['onglet_actif'] = self.onglet_actif
        context["famille"] = self.request.user.famille
        if not self.get_dict_onglet_actif().validation_auto:
            context['box_introduction'] = self.description_saisie + " " + _("Ces informations devront être validées par l'administrateur de l'application.")
        return context

    def get_object(self):
        return self.get_famille()

    def get_object(self):
        if not self.kwargs.get("idquotient"):
            return None
        return Quotient.objects.get(pk=self.kwargs.get("idquotient"))

    def get_success_url(self):
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url)


class Liste(Page, TemplateView):
    model = Quotient
    template_name = "portail/famille_quotients.html"

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['box_titre'] = _("Quotients familiaux")
        context['box_introduction'] = _("Cliquez sur le bouton Ajouter au bas de la page pour ajouter un nouveau quotient.")
        context['liste_quotients'] = Quotient.objects.filter(famille=self.request.user.famille).order_by("date_debut")
        return context


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "portail/fiche_edit.html"

    def form_valid(self, form):
        """ Enregistrement des modifications """
        # Enregistrement des valeurs
        instance = self.form_save(form)

        # Mémorisation du renseignement
        PortailRenseignement.objects.create(famille=self.get_famille(), individu=None, categorie=self.categorie, code="Nouveau quotient",
                                            nouvelle_valeur=json.dumps(str(instance), cls=DjangoJSONEncoder), idobjet=instance.pk)

        # Message de confirmation
        messages.add_message(self.request, messages.SUCCESS, _("Votre ajout a été enregistré"))

        # Demande une nouvelle certification
        self.Demande_nouvelle_certification()

        if self.object:
            self.save_historique(instance=self.object, form=form)

        return HttpResponseRedirect(self.get_success_url())


class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "portail/fiche_edit.html"


class Supprimer(Page, crud.Supprimer):
    template_name = "portail/fiche_delete.html"

    def Apres_suppression(self, objet=None):
        # Mémorisation du renseignement
        PortailRenseignement.objects.create(famille=self.get_famille(), individu=None, categorie=self.categorie, code="Quotient supprimé",
                                            ancienne_valeur=json.dumps(str(objet), cls=DjangoJSONEncoder))

        # Demande une nouvelle certification de la fiche
        self.Demande_nouvelle_certification()
