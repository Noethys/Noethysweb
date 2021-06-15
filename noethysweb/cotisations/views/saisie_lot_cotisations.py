# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views.base import CustomView
from django.views.generic import TemplateView
from core.utils import utils_texte
from django.http import HttpResponseRedirect
from django.shortcuts import render
import json
from fiche_famille.forms.famille_cotisations import Formulaire
from django.contrib import messages
from core.models import Famille, Rattachement, Cotisation, Prestation, Activite



def Get_table_beneficiaires(request):
    """ Renvoie le contenu de la table """
    categorie = request.POST.get("categorie")
    liste_selections = request.POST.get("liste_selections")
    if len(liste_selections) == 0:
        liste_selections = []
    else:
        liste_selections = [int(id) for id in liste_selections.split(";")]

    lignes = []

    if categorie == "familles":
        for famille in Famille.objects.all().order_by("nom"):
            lignes.append({
                "pk": famille.pk,
                "famille": famille.nom,
                "rue_resid": famille.rue_resid,
                "cp_resid": famille.cp_resid,
                "ville_resid": famille.ville_resid,
            })
    else:
        for rattachement in Rattachement.objects.select_related('individu', 'famille').all().order_by("individu__nom", "individu__prenom"):
            lignes.append({
                "pk": rattachement.pk,
                "individu": rattachement.individu.Get_nom(),
                "famille": rattachement.famille.nom,
                "rue_resid": rattachement.individu.rue_resid,
                "cp_resid": rattachement.individu.cp_resid,
                "ville_resid": rattachement.individu.ville_resid,
            })

    context = {"resultats": json.dumps(lignes), "categorie": categorie, "selections": json.dumps(liste_selections)}
    return render(request, "cotisations/selection_beneficiaires.html", context)



class View(CustomView, TemplateView):
    menu_code = "saisie_lot_cotisations"
    template_name = "core/crud/edit.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Saisir un lot d'adhésions"
        context['box_titre'] = "Saisir un lot d'adhésions"
        context['box_introduction'] = "Renseignez les paramètres des cotisations à générer et sélectionnez les familles ou individus concernés."
        if "form" not in kwargs:
            context['form'] = Formulaire(request=self.request)
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if form.is_valid() == False:
            if len(form.errors.as_data().keys()) > 1:
                return self.render_to_response(self.get_context_data(form=form))

        # Récupère la liste des bénéficiaires
        if form.cleaned_data.get("type_cotisation").type == "famille":
            mode = "familles"
            liste_beneficiaires = form.cleaned_data.get("beneficiaires_familles")
        else:
            liste_beneficiaires = form.cleaned_data.get("beneficiaires_individus")
            mode = "individus"
        liste_beneficiaires = [int(id) for id in liste_beneficiaires.split(";")] if liste_beneficiaires else []
        if len(liste_beneficiaires) == 0:
            messages.add_message(request, messages.ERROR, "Vous devez sélectionner au moins un bénéficiaire")
            return self.render_to_response(self.get_context_data(form=form))

        if mode == "familles":
            liste_objets = Famille.objects.filter(pk__in=liste_beneficiaires)
        else:
            liste_objets = Rattachement.objects.select_related('famille', 'individu').filter(pk__in=liste_beneficiaires)

        # Récupération des paramètres de la cotisation
        numero = form.cleaned_data["numero"]

        for objet in liste_objets:
            if mode == "familles":
                famille = objet
                individu = None
            else:
                famille = objet.famille
                individu = objet.individu

            # Création de la prestation
            prestation = None
            if form.cleaned_data["facturer"]:
                prestation = Prestation.objects.create(date=form.cleaned_data["date_facturation"], categorie="cotisation",
                                                       label=form.cleaned_data["label_prestation"], famille=famille,
                                                       montant_initial=form.cleaned_data["montant"], montant=form.cleaned_data["montant"])

            # Création de la cotisation
            cotisation = Cotisation.objects.create(
                date_creation_carte=form.cleaned_data["date_creation_carte"],
                numero=numero,
                date_debut=form.cleaned_data["date_debut"],
                date_fin=form.cleaned_data["date_fin"],
                observations=form.cleaned_data["observations"],
                famille=famille,
                individu=individu,
                prestation=prestation,
                type_cotisation=form.cleaned_data["type_cotisation"],
                unite_cotisation=form.cleaned_data["unite_cotisation"],
            )
            if form.cleaned_data["activites"]:
                cotisation.activites.set(form.cleaned_data["activites"])
            numero = utils_texte.Incrementer(numero)

        messages.add_message(request, messages.SUCCESS, "%d adhésions ont été créées avec succès" % len(liste_objets))
        return HttpResponseRedirect(reverse_lazy("cotisations_toc"))
