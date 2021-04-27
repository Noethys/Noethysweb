# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.base import CustomView
from django.views.generic import TemplateView
from core.utils import utils_dates, utils_infos_individus, utils_dictionnaires
from consommations.forms.edition_liste_conso_date import Formulaire as Form_date
from consommations.forms.edition_liste_conso_parametres import Formulaire as Form_parametres
from django.contrib import messages
import datetime, json
from django.http import JsonResponse
from core.models import Parametre



def get_data_profil(donnees=None):
    """ Récupère les données à sauvegarder dans le profil de configuration """
    form = Form_parametres(donnees)

    # Validation des paramètres
    if not form.is_valid():
        #todo : pas fonctionnel
        print("Erreurs =", form.errors.as_data())
        return JsonResponse({"erreur": "Les paramètres ne sont pas valides"}, status=401)

    # Suppression des données inutiles
    data = form.cleaned_data
    [data.pop(key) for key in ["profil", "groupes", "ecoles", "classes", "evenements"]]

    return data



def Generer_pdf(request):
    # Récupération des paramètres
    form_date = Form_date(request.POST)
    form_parametres = Form_parametres(request.POST)

    # Validation du form date
    if form_date.is_valid() == False:
        return JsonResponse({"erreur": "Veuillez sélectionner une date dans le calendrier"}, status=401)

    # Récupération des dates sélectionnées
    dates = form_date.cleaned_data.get("date")
    if ";" in dates:
        dates = [utils_dates.ConvertDateENGtoDate(date) for date in dates.split(";")]
    else:
        dates = [utils_dates.ConvertDateENGtoDate(dates),]

    # Validation du form paramètres
    if form_parametres.is_valid() == False:
        liste_erreurs = [erreur[0].message for field, erreur in form_parametres.errors.as_data().items()]
        return JsonResponse({"erreur": "Veuillez corriger les erreurs suivantes : %s" % ", ".join(liste_erreurs)}, status=401)

    # Préparation des paramètres
    dict_donnees = form_parametres.cleaned_data
    dict_donnees["dates"] = dates

    # Vérification des groupes
    if not dict_donnees["groupes"]:
        return JsonResponse({"erreur": "Vous devez cocher au moins une activité dans l'onglet Activités"}, status=401)

    # Création du PDF
    from consommations.utils import utils_impression_conso
    impression = utils_impression_conso.Impression(titre="Liste des consommations", dict_donnees=dict_donnees)
    if impression.erreurs:
        return JsonResponse({"erreur": impression.erreurs[0]}, status=401)
    nom_fichier = impression.Get_nom_fichier()
    return JsonResponse({"nom_fichier": nom_fichier})




class View(CustomView, TemplateView):
    menu_code = "edition_liste_conso"
    template_name = "consommations/edition_liste_conso.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Edition de la liste des consommations"
        dates = kwargs.get("dates", [datetime.date.today()])

        # Application du profil de configuration
        request_post = self.request.POST.copy()
        if request_post.get("application_profil"):
            parametre = Parametre.objects.get(idparametre=int(self.request.POST.get("profil")))
            initial_data = json.loads(parametre.parametre)
            [request_post.pop(key) for key in initial_data.keys() if key in request_post]
            request_post.update(initial_data)

        # Intégration des formulaires
        if "form_date" in kwargs:
            context['form_date'] = Form_date(request_post, dates=dates)
            context['form_parametres'] = Form_parametres(request_post, dates=dates)
        else:
            context['form_date'] = Form_date(dates=dates)
            context['form_parametres'] = Form_parametres(dates=dates)
        return context

    def post(self, request, **kwargs):
        form_date = Form_date(request.POST)
        form_parametres = Form_parametres(request.POST)

        # Validation du form date
        if form_date.is_valid() == False:
            return self.render_to_response(self.get_context_data(dates=[]))

        # Récupération des dates sélectionnées
        dates = form_date.cleaned_data.get("date")
        if ";" in dates:
            dates = [utils_dates.ConvertDateENGtoDate(date) for date in dates.split(";")]
        else:
            dates = [utils_dates.ConvertDateENGtoDate(dates),]

        # Validation du form paramètres
        if form_parametres.is_valid() == False:
            if "appliquer_date" not in request.POST:
                liste_erreurs = [erreur[0].message for field, erreur in form_parametres.errors.as_data().items()]
                messages.add_message(request, messages.ERROR, "Veuillez corriger les erreurs suivantes : %s" % ", ".join(liste_erreurs))
            return self.render_to_response(self.get_context_data(dates=dates))

        context = {"form_parametres": form_parametres, "form_date": form_date, "dates": dates}
        return self.render_to_response(self.get_context_data(**context))

