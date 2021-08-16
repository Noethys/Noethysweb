# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json
logger = logging.getLogger(__name__)
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
        form_kwargs["mode"] = getattr(self, "mode", None)
        return form_kwargs

    def form_save(self, form=None):
        """ Pour enregistrement direct des données """
        # super().form_valid(form)
        form.save()

    def Demande_nouvelle_certification(self):
        """ Demande une nouvelle certification de la fiche """
        logger.debug("%s : Demande une nouvelle certification de la fiche..." % self.request.user)
        if self.onglet_actif.startswith("individu_"):
            objet = self.get_rattachement()
        else:
            objet = self.get_famille()
        objet.certification_date = None
        objet.save()

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
                if self.verbe_action == "Ajouter":
                    messages.add_message(self.request, messages.SUCCESS, "Votre ajout a été enregistré")
                else:
                    messages.add_message(self.request, messages.SUCCESS, "Votre modification a été enregistrée")
            else:
                # Avec validation par l'admin
                valeurs = self.Get_valeurs(form.cleaned_data)
                for code in form.changed_data:
                    PortailRenseignement.objects.create(famille=self.get_famille(), individu=self.get_individu(), categorie=self.categorie, code=code, valeur=valeurs[code])
                if self.verbe_action == "Ajouter":
                    messages.add_message(self.request, messages.SUCCESS, "Votre ajout a été enregistré et transmis à l'administrateur")
                else:
                    messages.add_message(self.request, messages.SUCCESS, "Votre modification a été enregistrée et transmise à l'administrateur")

            # Affichage dans logger
            if self.verbe_action == "Modifier":
                logger.debug("%s : Modification des champs %s." % (self.request.user, ", ".join(form.changed_data)))

            # Demande une nouvelle certification
            self.Demande_nouvelle_certification()

        return HttpResponseRedirect(self.get_success_url())

    def Apres_suppression(self, objet=None):
        # Demande une nouvelle certification de la fiche
        self.Demande_nouvelle_certification()


class ConsulterBase(crud.Modifier):
    template_name = "portail/fiche_edit.html"
    mode = None
