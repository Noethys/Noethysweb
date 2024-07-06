# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.shortcuts import render
from core.models import AchatDemande
from core.views.base import CustomView
from core.utils import utils_parametres
from comptabilite.forms.suivi_achats import Formulaire as Form_parametres_suivi_achats


def Get_form_parametres(request):
    """ Renvoie le form des paramètres """
    parametres = utils_parametres.Get_categorie(categorie="suivi_achats", utilisateur=request.user, parametres={"periode": "14"})
    context = {"form_parametres_suivi_achats": Form_parametres_suivi_achats(request=request, initial={"periode": parametres["periode"]})}
    return render(request, "comptabilite/suivi_achats_parametres.html", context)


def Valider_form_parametres(request):
    """ Validation du form paramètres """
    form = Form_parametres_suivi_achats(request.POST)
    if not form.is_valid():
        return JsonResponse({"erreur": "Il y a une erreur dans les paramètres"}, status=401)
    utils_parametres.Set_categorie(categorie="suivi_achats", utilisateur=request.user, parametres={"periode": form.cleaned_data["periode"]})
    return JsonResponse({"resultat": True})


def Get_achats(request):
    """ Importation des demandes d'achats pour le widget """
    parametres = utils_parametres.Get_categorie(categorie="suivi_achats", utilisateur=request.user, parametres={"periode": "14"})
    date_max = datetime.date.today() + datetime.timedelta(days=int(parametres["periode"]))
    demandes = AchatDemande.objects.select_related("collaborateur").filter(date_echeance__lte=date_max, etat__lt=100).order_by("date_echeance")
    return demandes


class View(CustomView, TemplateView):
    menu_code = "suivi_achats"
    template_name = "comptabilite/suivi_achats_view.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Suivi des achats"
        context['demandes_achats'] = Get_achats(self.request)
        return context
