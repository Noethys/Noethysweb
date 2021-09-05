# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import AdresseMail
from parametrage.forms.adresses_mail import Formulaire
from django.http import JsonResponse
from outils.utils import utils_email
import json


def Envoyer_mail_test(request):
    # Récupère les paramètres de l'adresse d'expédition
    valeurs_form_adresse = json.loads(request.POST.get("form_adresse"))
    form_adresse = Formulaire(valeurs_form_adresse, request=self.request)
    if form_adresse.is_valid() == False:
        return JsonResponse({"erreur": "Veuillez compléter les paramètres de l'adresse d'expédition"}, status=401)

    # Récupère l'adresse de destination du test
    adresse_destination = request.POST.get("adresse_destination")
    if not adresse_destination:
        return JsonResponse({"erreur": "Veuillez saisir une adresse de destination pour le test d'envoi"}, status=401)

    # Met toutes les données dans un dict
    dict_options = form_adresse.cleaned_data
    dict_options.update({"adresse_destination": adresse_destination})

    # Envoi du message
    resultat = utils_email.Envoyer_mail_test(request=request, dict_options=dict_options)
    return JsonResponse({"resultat": resultat})



class Page(crud.Page):
    model = AdresseMail
    url_liste = "adresses_mail_liste"
    url_ajouter = "adresses_mail_ajouter"
    url_modifier = "adresses_mail_modifier"
    url_supprimer = "adresses_mail_supprimer"
    description_liste = "Voici ci-dessous la liste des adresses d'expédition d'emails."
    description_saisie = "Saisissez toutes les informations concernant l'adresse d'expédition à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une adresse d'expédition"
    objet_pluriel = "des adresses d'expédition"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]
    compatible_demo = False


class Liste(Page, crud.Liste):
    model = AdresseMail

    def get_queryset(self):
        return AdresseMail.objects.filter(self.Get_filtres("Q"), self.Get_condition_structure())

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ['idadresse', 'adresse', 'moteur', 'defaut']

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        defaut = columns.TextColumn("Défaut", sources="defaut", processor='Get_default')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idadresse', 'adresse', 'moteur', 'defaut']
            ordering = ['adresse']

        def Get_default(self, instance, **kwargs):
            return "<i class='fa fa-check text-success'></i>" if instance.defaut else ""


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

    def form_valid(self, form):
        # Si le Défaut a été coché, on supprime le Défaut des autres types
        if form.instance.defaut:
            self.model.objects.filter(defaut=True).update(defaut=False)
        return super().form_valid(form)


class Modifier(Page, crud.Modifier):
    form_class = Formulaire

    def form_valid(self, form):
        # Si le Défaut a été coché, on supprime le Défaut des autres types
        if form.instance.defaut:
            self.model.objects.filter(defaut=True).update(defaut=False)
        return super().form_valid(form)


class Supprimer(Page, crud.Supprimer):
    pass

    def delete(self, request, *args, **kwargs):
        reponse = super(Supprimer, self).delete(request, *args, **kwargs)
        if reponse.status_code != 303:
            # Si le défaut a été supprimé, on le réattribue à un autre type
            if len(self.model.objects.filter(defaut=True)) == 0:
                objet = self.model.objects.all().first()
                if objet:
                    objet.defaut = True
                    objet.save()
        return reponse
