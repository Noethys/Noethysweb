# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views import crud
from core.models import Famille
from fiche_famille.forms.famille_portail import Formulaire
from fiche_famille.views.famille import Onglet
from fiche_famille.utils import utils_internet
from django.http import JsonResponse


def Impression_pdf(request):
    # Récupération des données du formulaire
    internet_identifiant = request.POST.get("internet_identifiant")
    internet_mdp = request.POST.get("internet_mdp")
    idfamille = int(request.POST.get("idfamille"))

    # Récupération des valeurs de fusion
    famille = Famille.objects.get(pk=idfamille)
    champs = {
        "{NOM_FAMILLE}": famille.nom,
        "{IDENTIFIANT_INTERNET}": internet_identifiant,
        "{MOTDEPASSE_INTERNET}": internet_mdp,
    }
    return JsonResponse({"categorie": "portail", "champs": champs, "idfamille": idfamille})



def Regenerer_identifiant(request):
    IDfamille = int(request.POST.get("idfamille"))
    identifiant = utils_internet.CreationIdentifiant(IDfamille=IDfamille)
    return JsonResponse({"identifiant": identifiant})

def Regenerer_mdp(request):
    mdp = utils_internet.CreationMDP()
    return JsonResponse({"mdp": mdp})


class Modifier(Onglet, crud.Modifier):
    form_class = Formulaire
    template_name = "fiche_famille/famille_portail.html"

    def get_context_data(self, **kwargs):
        context = super(Modifier, self).get_context_data(**kwargs)
        context['box_titre'] = "Portail"
        context['box_introduction'] = "Vous pouvez modifier ici les paramètres du compte internet de la famille."
        context['onglet_actif'] = "portail"
        return context

    def get_success_url(self):
        return reverse_lazy("famille_resume", kwargs={'idfamille': self.kwargs.get('idfamille', None)})

    def get_object(self):
        return Famille.objects.get(pk=self.kwargs['idfamille'])

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idindividu au formulaire """
        form_kwargs = super(Modifier, self).get_form_kwargs(**kwargs)
        form_kwargs["idfamille"] = self.Get_idfamille()
        return form_kwargs
