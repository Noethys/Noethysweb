# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.db import models
from core.models import Rattachement
from portail.views.base import CustomView
from portail.utils import utils_onglets
from core.views import crud
from django.contrib import messages
from django.http import HttpResponseRedirect
from core.models import PortailRenseignement
from django.db.models.query import QuerySet
from django.core.serializers.json import DjangoJSONEncoder
import json



class Onglet(CustomView):
    menu_code = "portail_renseignements"
    rattachement = None
    onglet_actif = None
    dict_onglet_actif = None

    def get_context_data(self, **kwargs):
        context = super(Onglet, self).get_context_data(**kwargs)
        if self.onglet_actif.startswith("individu_"):
            context['page_titre'] = "Fiche individuelle"
            context['rattachement'] = self.get_rattachement()
            context['liste_onglets'] = utils_onglets.Get_onglets(categorie=self.get_categorie_rattachement())
        else:
            context['page_titre'] = "Fiche famille"
            context['liste_onglets'] = utils_onglets.Get_onglets(categorie="famille")
        return context

    def get_rattachement(self):
        if not self.rattachement and self.onglet_actif.startswith("individu_"):
            self.rattachement = Rattachement.objects.select_related("individu", "famille").get(pk=self.kwargs['idrattachement'])
        return self.rattachement

    def get_categorie_rattachement(self):
        rattachement = self.get_rattachement()
        return rattachement.categorie if rattachement else None

    def get_famille(self):
        return self.request.user.famille

    def get_individu(self):
        rattachement = self.get_rattachement()
        return rattachement.individu if rattachement else None

    def get_dict_onglet_actif(self):
        if not self.dict_onglet_actif:
            if self.onglet_actif.startswith("individu_"):
                self.dict_onglet_actif = utils_onglets.Get_onglet(self.onglet_actif)
            else:
                self.dict_onglet_actif = utils_onglets.Get_onglet(self.onglet_actif)
        return self.dict_onglet_actif

    def test_func(self):
        """ Vérifie que l'utilisateur peut se connecter à cette page """
        if not super(Onglet, self).test_func():
            return False
        if self.get_famille() != self.request.user.famille:
            return False
        return True

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Onglet, self).get_form_kwargs(**kwargs)
        if self.onglet_actif.startswith("individu_"):
            form_kwargs["rattachement"] = self.get_rattachement()
        else:
            form_kwargs["famille"] = self.get_famille()
        return form_kwargs




class ConsulterBase(crud.Modifier):
    template_name = "portail/fiche_edit.html"
    mode = None

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(ConsulterBase, self).get_form_kwargs(**kwargs)
        form_kwargs["mode"] = self.mode
        return form_kwargs

    def form_save(self, form=None):
        """ Pour enregistrement direct des données """
        # super().form_valid(form)
        form.save()

    def Get_valeurs(self, valeurs={}):
        """ Pour modifier des valeurs à la volée """
        for key, valeur in valeurs.items():

            # Transforme une instance de model en pk
            if isinstance(valeur, (models.Model, models.base.ModelBase)):
                valeur = valeur.pk

            # Transforme les queryset en liste de pk
            if isinstance(valeur, QuerySet):
                valeur = [instance.pk for instance in valeur.all()]

            # Transforme la valeur en json
            valeurs[key] = json.dumps(valeur, cls=DjangoJSONEncoder)

        return valeurs

    def form_valid(self, form):
        """ Enregistrement des modifications """
        if not form.changed_data:
            messages.add_message(self.request, messages.INFO, "Aucune modification n'a été enregistrée")
        else:
            if self.get_dict_onglet_actif().validation_auto:
                # Sans validation par l'admin
                self.form_save(form)
                messages.add_message(self.request, messages.SUCCESS, "Votre modification a été enregistrée")
            else:
                # Avec validation par l'admin
                valeurs = self.Get_valeurs(form.cleaned_data)
                for code in form.changed_data:
                    PortailRenseignement.objects.create(famille=self.get_famille(), individu=self.get_individu(), categorie=self.categorie, code=code, valeur=valeurs[code])
                messages.add_message(self.request, messages.SUCCESS, "Votre modification a été enregistrée et transmise à l'administrateur")
        return HttpResponseRedirect(self.get_success_url())
