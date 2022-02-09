# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.urls import reverse_lazy
from django.http import JsonResponse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import ConfigurationSMS
from outils.utils import utils_sms
from parametrage.forms.configurations_sms import Formulaire


def Envoyer_sms_test(request):
    # Récupère les paramètres
    valeurs_configuration = json.loads(request.POST.get("configuration"))
    form_configuration = Formulaire(valeurs_configuration, request=request)
    if form_configuration.is_valid() == False:
        return JsonResponse({"erreur": "Veuillez compléter les paramètres de la configuration"}, status=401)

    # Récupère le numéro de destination du test
    numero_destination = request.POST.get("numero_destination")
    if not numero_destination:
        return JsonResponse({"erreur": "Veuillez saisir un numéro de téléphone pour le test d'envoi"}, status=401)

    # Met toutes les données dans un dict
    dict_options = form_configuration.cleaned_data
    dict_options.update({"numero_destination": numero_destination})

    # Envoi du message
    resultat = utils_sms.Envoyer_sms_test(request=request, dict_options=dict_options)
    return JsonResponse({"resultat": resultat})


class Page(crud.Page):
    model = ConfigurationSMS
    url_liste = "configurations_sms_liste"
    url_ajouter = "configurations_sms_ajouter"
    url_modifier = "configurations_sms_modifier"
    url_supprimer = "configurations_sms_supprimer"
    description_liste = "Voici ci-dessous la liste des configurations SMS."
    description_saisie = "Saisissez toutes les informations concernant la configuration à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une configuration SMS"
    objet_pluriel = "des configurations SMS"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]
    compatible_demo = False


class Liste(Page, crud.Liste):
    model = ConfigurationSMS

    def get_queryset(self):
        return ConfigurationSMS.objects.filter(self.Get_filtres("Q"), self.Get_condition_structure())

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idconfiguration", "moteur", "nom_exp", "solde"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idconfiguration", "moteur", "nom_exp", "solde"]
            ordering = ["nom_exp"]

        def Get_default(self, instance, **kwargs):
            return "<i class='fa fa-check text-success'></i>" if instance.defaut else ""


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass
