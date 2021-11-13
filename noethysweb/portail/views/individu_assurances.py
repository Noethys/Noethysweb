# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, datetime
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.db.models import Q
from core.views import crud
from core.models import Inscription, Assurance
from portail.forms.individu_assurances import Formulaire
from portail.views.fiche import Onglet, ConsulterBase
from portail.forms.assureurs import Formulaire as Formulaire_assureur
from individus.utils import utils_assurances


def Ajouter_assureur(request):
    """ Ajouter un assureur dans la liste de choix """
    valeurs = json.loads(request.POST.get("valeurs"))

    # Formatage des champs
    valeurs["nom"] = valeurs["nom"].upper()
    valeurs["rue_resid"] = valeurs["rue_resid"].title()
    valeurs["ville_resid"] = valeurs["ville_resid"].upper()

    # Vérification des données saisies
    form = Formulaire_assureur(valeurs)
    if not form.is_valid():
        messages_erreurs = ["%s : %s" % (field.title(), erreur[0].message) for field, erreur in form.errors.as_data().items()]
        return JsonResponse({"erreur": ", ".join(messages_erreurs)}, status=401)

    # Sauvegarde de l'assureur
    instance = form.save()
    return JsonResponse({"id": instance.pk, "nom": instance.Get_nom(afficher_ville=True)})


class Page(Onglet):
    model = Assurance
    url_liste = "portail_individu_assurances"
    url_ajouter = "portail_individu_assurances_ajouter"
    url_modifier = "portail_individu_assurances_modifier"
    url_supprimer = "portail_individu_assurances_supprimer"
    description_liste = "Cliquez sur le bouton Ajouter au bas de la page pour ajouter une nouvelle assurance."
    description_saisie = "Saisissez les informations concernant l'assurance et cliquez sur le bouton Enregistrer."
    objet_singulier = "une assurance"
    objet_pluriel = "des assurances"
    onglet_actif = "individu_assurances"
    categorie = "individu_assurances"


    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['onglet_actif'] = self.onglet_actif
        if not self.get_dict_onglet_actif().validation_auto:
            context['box_introduction'] = self.description_saisie + " Ces informations devront être validées par l'administrateur de l'application."
        context['form_ajout'] = Formulaire_assureur()
        return context

    def get_object(self):
        if not self.kwargs.get("idassurance"):
            return None
        return Assurance.objects.get(pk=self.kwargs.get("idassurance"))

    def get_success_url(self):
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idrattachement': self.kwargs['idrattachement']})


class Liste(Page, TemplateView):
    model = Assurance
    template_name = "portail/individu_assurances.html"

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['box_titre'] = "Assurances"
        context['box_introduction'] = "Cliquez sur le bouton Ajouter au bas de la page pour ajouter une nouvelle assurance."
        context['liste_assurances'] = Assurance.objects.filter(famille=self.get_rattachement().famille, individu=self.get_rattachement().individu).order_by("-date_debut")

        # Recherche si l'assurance de l'individu est manquante
        conditions = Q(famille=self.request.user.famille) & Q(individu=self.get_rattachement().individu) & (Q(date_fin__isnull=True) | Q(date_fin__gte=datetime.date.today()))
        inscriptions = Inscription.objects.select_related("activite").filter(conditions)
        context["assurance_manquante"] = len(utils_assurances.Get_assurances_manquantes_by_inscriptions(famille=self.request.user.famille, inscriptions=inscriptions)) > 0

        return context


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "portail/individu_assureur.html"

class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "portail/individu_assureur.html"

class Supprimer(Page, crud.Supprimer):
    template_name = "portail/fiche_delete.html"
