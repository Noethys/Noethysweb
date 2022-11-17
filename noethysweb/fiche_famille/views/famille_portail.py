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
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages


def Envoyer_codes(request):
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


class Consulter(Onglet, crud.Modifier):
    form_class = Formulaire
    template_name = "fiche_famille/famille_portail.html"
    mode = "CONSULTATION"

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super(Consulter, self).get_context_data(**kwargs)
        context['box_titre'] = "Portail"
        context['box_introduction'] = "Cliquez sur le bouton Modifier pour modifier une des informations ci-dessous."
        context['onglet_actif'] = "portail"
        return context

    def get_object(self):
        return Famille.objects.get(pk=self.kwargs['idfamille'])

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Consulter, self).get_form_kwargs(**kwargs)
        form_kwargs["idfamille"] = self.Get_idfamille()
        return form_kwargs


class Modifier(Consulter):
    mode = "EDITION"

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super(Modifier, self).get_context_data(**kwargs)
        context['box_introduction'] = "Vous pouvez modifier ici les paramètres du compte internet de la famille."
        return context

    def get_success_url(self):
        return reverse_lazy("famille_portail", kwargs={'idfamille': self.kwargs.get('idfamille', None)})

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, idfamille=self.kwargs['idfamille'], request=self.request, mode=self.mode)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        # Importation de la famille
        famille = self.get_object()
        utilisateur = famille.utilisateur

        # Récupération des données
        internet_actif = form.cleaned_data.get("internet_actif")
        internet_identifiant = form.cleaned_data.get("internet_identifiant")
        mdp = form.cleaned_data.get("internet_mdp")
        internet_categorie = form.cleaned_data.get("internet_categorie")

        # Si changement de l'état actif
        if internet_actif != famille.internet_actif:
            famille.internet_actif = internet_actif
            utilisateur.is_active = internet_actif

        # Si changement de l'identifiant
        if internet_identifiant != famille.internet_identifiant:
            if Famille.objects.filter(internet_identifiant=internet_identifiant).exclude(famille=famille).exists():
                messages.add_message(request, messages.ERROR, "Cet identifiant a déjà été attribué à une autre famille !")
                return self.render_to_response(self.get_context_data(form=form))
            famille.internet_identifiant = internet_identifiant
            utilisateur.username = internet_identifiant

        # Si changement de mot de passe
        if mdp != famille.internet_mdp:
            famille.internet_mdp = mdp
            utilisateur.set_password(mdp)
            utilisateur.force_reset_password = True

        # Si changement de categorie
        if internet_categorie != famille.internet_categorie:
            famille.internet_categorie = internet_categorie

        # Enregistrement
        utilisateur.save()
        famille.save()

        return HttpResponseRedirect(reverse_lazy("famille_portail", args=(self.kwargs['idfamille'],)))
