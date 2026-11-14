# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.contrib import messages
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import View
from core.views.base import CustomView
from core.utils import utils_valeurs_defaut_collaborateurs


def Bouton(liste):
    """ Bouton "Importer les valeurs par défaut" à ajouter dans boutons_liste d'une page de paramétrage """
    return {"label": "Importer les valeurs par défaut", "classe": "btn btn-default", "icone": "fa fa-download", "post": True,
            "href": reverse_lazy("valeurs_defaut_collaborateurs_importer", kwargs={"liste": liste}),
            "confirmation": "Ajouter les valeurs proposées par défaut ? Les valeurs déjà présentes ne seront pas modifiées."}


class Importer(CustomView, View):
    """ Ajoute les valeurs par défaut absentes d'une liste de paramétrage (accès soumis à la permission de la liste) """
    http_method_names = ["post"]

    def setup(self, request, *args, **kwargs):
        super(Importer, self).setup(request, *args, **kwargs)
        if kwargs.get("liste") not in utils_valeurs_defaut_collaborateurs.LISTES:
            raise Http404
        self.fonction, self.url_liste, self.singulier, self.pluriel = utils_valeurs_defaut_collaborateurs.LISTES[kwargs["liste"]]
        self.menu_code = self.url_liste

    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            resultat = self.fonction()
        nbre = resultat["ajouts"]
        if not nbre:
            messages.add_message(request, messages.INFO, "Toutes les valeurs par défaut sont déjà présentes.")
        else:
            texte = "%d %s %s." % (nbre, self.singulier if nbre == 1 else self.pluriel, "ajouté" if nbre == 1 else "ajoutés")
            if self.pluriel.startswith("catégories"):
                texte = texte.replace("ajouté", "ajoutée")
            if resultat.get("categories"):
                texte += " %d catégorie%s d'évènements associée%s %s également été créée%s." % (
                    resultat["categories"], *(("s", "s", "ont", "s") if resultat["categories"] > 1 else ("", "", "a", "")))
            if resultat.get("qualifications"):
                texte += " %d type%s de qualification%s associé%s %s également été créé%s." % (
                    resultat["qualifications"], *(("s", "s", "s", "ont", "s") if resultat["qualifications"] > 1 else ("", "", "", "a", "")))
            messages.add_message(request, messages.SUCCESS, texte)
        return redirect(self.url_liste)
