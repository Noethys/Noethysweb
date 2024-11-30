# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.utils.dateparse import parse_date
from core.views import crud
from core.models import Famille, Utilisateur
from fiche_famille.forms.famille_portail import Formulaire
from fiche_famille.views.famille import Onglet
from fiche_famille.utils import utils_internet


def Envoyer_codes(request):
    # Récupération des données du formulaire
    internet_identifiant = request.POST.get("internet_identifiant")
    internet_mdp = request.POST.get("internet_mdp")
    date_expiration_mdp = request.POST.get("date_expiration_mdp")
    idfamille = int(request.POST.get("idfamille"))

    # Récupération des valeurs de fusion
    famille = Famille.objects.get(pk=idfamille)
    champs = {
        "{NOM_FAMILLE}": famille.nom,
        "{IDENTIFIANT_INTERNET}": internet_identifiant,
        "{MOTDEPASSE_INTERNET}": internet_mdp,
        "{DATE_EXPIRATION_MOTDEPASSE}": parse_date(date_expiration_mdp[:10]).strftime("%d/%m/%Y") if date_expiration_mdp and date_expiration_mdp != "None" else "",
    }
    return JsonResponse({"categorie": "portail", "champs": champs, "idfamille": idfamille})


def Regenerer_identifiant(request):
    IDfamille = int(request.POST.get("idfamille"))
    identifiant = utils_internet.CreationIdentifiant(IDfamille=IDfamille)
    return JsonResponse({"identifiant": identifiant})


def Regenerer_mdp(request):
    mdp, date_expiration_mdp = utils_internet.CreationMDP()
    return JsonResponse({"mdp": mdp, "date_expiration_mdp": str(date_expiration_mdp)})


class Consulter(Onglet, crud.Modifier):
    form_class = Formulaire
    template_name = "fiche_famille/famille_portail.html"
    mode = "CONSULTATION"

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super(Consulter, self).get_context_data(**kwargs)
        context['box_titre'] = "Portail"
        context['box_introduction'] = "Cliquez sur le bouton Modifier pour modifier une des informations ci-dessous."
        if not self.request.user.has_perm("core.famille_portail_modifier"):
            context['box_introduction'] = "Vous n'avez pas l'autorisation de modifier les informations de cette page."
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

    def test_func_page(self):
        return self.request.user.has_perm("core.famille_portail_modifier")

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
        internet_reservations = form.cleaned_data.get("internet_reservations")
        date_expiration_mdp = form.cleaned_data.get("date_expiration_mdp")
        individus_masques = form.cleaned_data.get("individus_masques")
        blocage_impayes_off = form.cleaned_data.get("blocage_impayes_off")

        # Si changement de l'état actif
        if internet_actif != famille.internet_actif:
            famille.internet_actif = internet_actif
            utilisateur.is_active = internet_actif

        # Si changement de l'identifiant
        if internet_identifiant != famille.internet_identifiant:
            if Utilisateur.objects.filter(username__iexact=internet_identifiant).exists():
                messages.add_message(request, messages.ERROR, "Cet identifiant a déjà été attribué à une autre famille !")
                return self.render_to_response(self.get_context_data(form=form))
            famille.internet_identifiant = internet_identifiant
            utilisateur.username = internet_identifiant

        # Si changement de mot de passe
        if mdp != famille.internet_mdp:
            famille.internet_mdp = mdp
            utilisateur.set_password(mdp)
            utilisateur.force_reset_password = True
            utilisateur.date_expiration_mdp = date_expiration_mdp

        # Si changement de categorie
        if internet_categorie != famille.internet_categorie:
            famille.internet_categorie = internet_categorie

        if internet_reservations != famille.internet_reservations:
            famille.internet_reservations = internet_reservations

        # Enregistrement
        utilisateur.save()

        famille.blocage_impayes_off = blocage_impayes_off
        famille.save()

        # Enregistrement des individus masqués
        famille.individus_masques.set(individus_masques)

        return HttpResponseRedirect(reverse_lazy("famille_portail", args=(self.kwargs['idfamille'],)))
