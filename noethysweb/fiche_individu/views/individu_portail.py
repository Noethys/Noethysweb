# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages
from core.views import crud
from core.models import Individu, Utilisateur
from fiche_individu.forms.individu_portail import Formulaire
from fiche_individu.views.individu import Onglet
from fiche_famille.utils import utils_internet


def Envoyer_codes(request):
    # Récupération des données du formulaire
    internet_identifiant = request.POST.get("internet_identifiant")
    internet_mdp = request.POST.get("internet_mdp")
    idindividu = int(request.POST.get("idindividu"))

    # Récupération des valeurs de fusion
    individu = Individu.objects.get(pk=idindividu)
    champs = {
        "{NOM_INDIVIDU": individu.nom,
        "{IDENTIFIANT_INTERNET}": internet_identifiant,
        "{MOTDEPASSE_INTERNET}": internet_mdp,
    }
    return JsonResponse({"categorie": "portail", "champs": champs, "idindividu": idindividu})

def Regenerer_identifiant(request):
    IDindividu = int(request.POST.get("idindividu"))
    identifiant = utils_internet.CreationIdentifiantIndividu(IDindividu=IDindividu)
    return JsonResponse({"identifiant": identifiant})


def Regenerer_mdp(request):
    mdp, date_expiration_mdp = utils_internet.CreationMDP()
    return JsonResponse({"mdp": mdp, "date_expiration_mdp": str(date_expiration_mdp)})


class Consulter(Onglet, crud.Modifier):
    form_class = Formulaire
    template_name = "fiche_individu/individu_portail.html"
    mode = "CONSULTATION"

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super(Consulter, self).get_context_data(**kwargs)
        context['box_titre'] = "Portail"
        context['box_introduction'] = "Cliquez sur le bouton Modifier pour modifier une des informations ci-dessous."
        if not self.request.user.has_perm("core.individu_portail_modifier"):
            context['box_introduction'] = "Vous n'avez pas l'autorisation de modifier les informations de cette page."
        context['onglet_actif'] = "portail"
        return context

    def get_object(self):
        return Individu.objects.get(pk=self.kwargs['idindividu'])

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Consulter, self).get_form_kwargs(**kwargs)
        form_kwargs["idindividu"] = self.Get_idindividu()
        return form_kwargs


class Modifier(Consulter):
    mode = "EDITION"

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super(Modifier, self).get_context_data(**kwargs)
        context['box_introduction'] = "Vous pouvez modifier ici les paramètres du compte internet de l'individu."
        return context

    def test_func_page(self):
        return self.request.user.has_perm("core.individu_portail_modifier")

    def get_success_url(self):
        return reverse_lazy("individu_portail", kwargs={'idindividu': self.kwargs.get('idindividu', None)})

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, idindividu=self.kwargs['idindividu'], request=self.request, mode=self.mode)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        # Importation de l'individu'
        individu = self.get_object()
        utilisateur = individu.utilisateur

        # Récupération des données
        internet_actif = form.cleaned_data.get("internet_actif")
        internet_identifiant = form.cleaned_data.get("internet_identifiant")
        mdp = form.cleaned_data.get("internet_mdp")

        internet_categorie = form.cleaned_data.get("internet_categorie")
        date_expiration_mdp = form.cleaned_data.get("date_expiration_mdp")
        individus_masques = form.cleaned_data.get("individus_masques")
        blocage_impayes_off = form.cleaned_data.get("blocage_impayes_off")

        # Si changement de l'état actif
        if internet_actif != individu.internet_actif:
            individu.internet_actif = internet_actif
            utilisateur.is_active = internet_actif

        # Si changement de l'identifiant
        if internet_identifiant != individu.internet_identifiant:
            if Utilisateur.objects.filter(username__iexact=internet_identifiant).exists():
                messages.add_message(request, messages.ERROR, "Cet identifiant a déjà été attribué à une autre individu !")
                return self.render_to_response(self.get_context_data(form=form))
            individu.internet_identifiant = internet_identifiant
            utilisateur.username = internet_identifiant

        # Si changement de mot de passe
        if mdp != individu.internet_mdp:
            individu.internet_mdp = mdp
            utilisateur.set_password(mdp)
            utilisateur.force_reset_password = True
            utilisateur.date_expiration_mdp = date_expiration_mdp

        # Si changement de categorie
        if internet_categorie != individu.internet_categorie:
            individu.internet_categorie = internet_categorie

        # Enregistrement
        utilisateur.save()

        individu.blocage_impayes_off = blocage_impayes_off
        individu.save()

        # Enregistrement des individus masqués
        individu.individus_masques.set(individus_masques)

        return HttpResponseRedirect(reverse_lazy("individu_portail", args=(self.kwargs['idfamille'],self.kwargs['idindividu'],)))
