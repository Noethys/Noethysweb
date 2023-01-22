# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView
from core.views import crud
from core.models import Prestation
from fiche_famille.forms.famille_prestations_modele import Formulaire, Formulaire_selection_modele
from fiche_famille.views.famille import Onglet


class Page(Onglet):
    model = Prestation
    description_saisie = "Saisissez toutes les informations concernant la prestation et cliquez sur le bouton Enregistrer."
    objet_singulier = "une prestation"
    objet_pluriel = "des prestations"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['onglet_actif'] = "prestations"
        return context

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idindividu au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idfamille"] = self.Get_idfamille()
        form_kwargs["idmodele"] = self.kwargs.get("idmodele", None)
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        return reverse_lazy("famille_prestations_liste", kwargs={'idfamille': self.kwargs.get('idfamille', None)})


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "fiche_famille/famille_edit.html"


class Selection_modele(Onglet, TemplateView):
    template_name = "fiche_famille/famille_edit.html"

    def get_context_data(self, **kwargs):
        context = super(Selection_modele, self).get_context_data(**kwargs)
        if not hasattr(self, "verbe_action"):
            context['box_titre'] = "Sélection d'un modèle de prestation"
        context['box_introduction'] = "Vous devez commencer par sélectionner le modèle de prestation à appliquer. Les modèles peuvent être créés depuis le menu Paramétrage."
        context['onglet_actif'] = "prestations"
        context['form'] = Formulaire_selection_modele(request=self.request)
        return context

    def post(self, request, **kwargs):
        idmodele = int(request.POST.get("modele"))
        return HttpResponseRedirect(reverse_lazy("famille_prestations_ajouter_modele", args=(self.Get_idfamille(), idmodele)))

    def Get_annuler_url(self):
        return reverse_lazy("famille_prestations_liste", kwargs={'idfamille': self.kwargs.get('idfamille', None)})
