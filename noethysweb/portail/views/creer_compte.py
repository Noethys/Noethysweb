# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime
logger = logging.getLogger(__name__)
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.http import HttpResponseRedirect
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator
from core.models import Famille, Utilisateur, Individu, Rattachement, PortailRenseignement
from core.utils import utils_portail
from fiche_famille.utils import utils_internet
from portail.forms.creer_compte import FormCreerCompte
from portail.views.login import ClassCommuneLogin
from portail.utils import utils_email


class CreerCompteView(ClassCommuneLogin, TemplateView):
    template_name = "portail/creer_compte/demande.html"

    def dispatch(self, request, *args, **kwargs):
        parametres_portail = utils_portail.Get_dict_parametres()
        if not parametres_portail.get("connexion_creation_compte", False):
            return redirect("portail_connexion")
        return super(CreerCompteView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(CreerCompteView, self).get_context_data(**kwargs)
        if "form" not in kwargs:
            context["form"] = FormCreerCompte()
        return context

    def post(self, request, **kwargs):
        # Validation du form
        form = FormCreerCompte(request.POST)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        # Création de la fiche famille
        famille = Famille.objects.create()
        logger.debug("Création autonome de la famille ID%d depuis le portail." % famille.pk)
        internet_identifiant = utils_internet.CreationIdentifiant(IDfamille=famille.pk)
        famille.internet_identifiant = internet_identifiant
        famille.internet_mdp = "*****"
        utilisateur = Utilisateur(username=internet_identifiant, categorie="famille", force_reset_password=False, date_expiration_mdp=None)
        utilisateur.save()
        utilisateur.set_password(form.cleaned_data["mdp1"])
        utilisateur.is_active = False
        utilisateur.save()
        famille.utilisateur = utilisateur
        famille.memo = "Fiche famille créée sur le portail le %s." % datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        famille.save()

        # Création du payeur
        payeur = Individu.objects.create(
            civilite=form.cleaned_data["civilite"],
            nom=form.cleaned_data["nom"].upper(),
            prenom=form.cleaned_data["prenom"].title(),
            mail=form.cleaned_data["email"],
        )
        Rattachement.objects.create(categorie=1, titulaire=True, famille=famille, individu=payeur)
        famille.Maj_infos()

        # Mémorisation dans l'historique
        PortailRenseignement.objects.create(famille=famille, categorie="nouvelle_famille", code="Nouvelle fiche famille", idobjet=famille.pk)

        # Envoi du mail avec token
        opts = {
            "nom_template_sujet": "portail/creer_compte/emails/activation_sujet.txt",
            "nom_template_html": "portail/creer_compte/emails/activation_html.html",
            "nom_template_texte": "portail/creer_compte/emails/activation_texte.html",
            "utilisateur": utilisateur, "request": self.request,
            "extra_email_context": {"prenom": form.cleaned_data["prenom"]},
            "token": default_token_generator.make_token(utilisateur),
        }
        resultat = utils_email.Envoyer_email(**opts)
        if resultat != True:
            messages.add_message(request, messages.ERROR, resultat)
            return self.render_to_response(self.get_context_data(form=form))

        logger.debug("Famille ID%d : Mail d'activation envoyé à %s." % (famille.pk, form.cleaned_data["email"]))
        return HttpResponseRedirect(reverse_lazy("portail_creer_compte_attente"))


def Activer(request, uidb64, token):
    # Retrouve l'utilisateur à partir du token
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        utilisateur = Utilisateur.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Utilisateur.DoesNotExist):
        utilisateur = None

    if utilisateur is not None and default_token_generator.check_token(utilisateur, token):
        # Activation du compte utilisateur
        utilisateur.is_active = True
        utilisateur.save()
        logger.debug("Famille ID%d : Activation réussie." % utilisateur.famille.pk)

        # Envoi des informations de connexion
        opts = {
            "nom_template_sujet": "portail/creer_compte/emails/confirmation_sujet.txt",
            "nom_template_html": "portail/creer_compte/emails/confirmation_html.html",
            "nom_template_texte": "portail/creer_compte/emails/confirmation_texte.html",
            "utilisateur": utilisateur, "request": request,
            "extra_email_context": {"identifiant": utilisateur.famille.internet_identifiant},
            "token": default_token_generator.make_token(utilisateur),
        }
        resultat = utils_email.Envoyer_email(**opts)
        return HttpResponseRedirect(reverse_lazy("portail_creer_compte_active"))
    else:
        logger.debug("Tentative d'activation échouée pour utilisateur %s." % utilisateur)
        return HttpResponseRedirect(reverse_lazy("portail_creer_compte_probleme"))


class CreerCompteAttenteView(ClassCommuneLogin, TemplateView):
    template_name = "portail/creer_compte/attente.html"


class CreerCompteActiveView(ClassCommuneLogin, TemplateView):
    template_name = "portail/creer_compte/active.html"


class CreerCompteProblemeView(ClassCommuneLogin, TemplateView):
    template_name = "portail/creer_compte/probleme.html"
