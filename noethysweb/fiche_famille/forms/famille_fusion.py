# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.urls import reverse
from django_select2.forms import HeavySelect2Widget


def Get_widget(placeholder, url):
    """ Select2 alimenté par une vue AJAX dédiée (indépendant du cache de django-select2) """
    return HeavySelect2Widget({"lang": "fr", "data-width": "100%", "data-minimum-input-length": 2, "data-ajax--type": "GET",
                               "data-placeholder": placeholder, "data-allow-clear": "true"}, data_url=url)


class Formulaire_selection_famille(forms.Form):
    famille = forms.ChoiceField(label="Famille en double", required=False)

    def __init__(self, *args, **kwargs):
        idfamille = kwargs.pop("idfamille")
        super(Formulaire_selection_famille, self).__init__(*args, **kwargs)
        self.fields["famille"].widget = Get_widget("Saisissez le nom de la famille ou son ID", "%s?exclure=%d" % (reverse("ajax_fusion_rechercher_familles"), idfamille))


class Formulaire_selection_individu(forms.Form):
    doublon = forms.ChoiceField(label="Fiche en double", required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire_selection_individu, self).__init__(*args, **kwargs)
        self.fields["doublon"].widget = Get_widget("Saisissez le nom, le prénom ou l'ID de l'individu", reverse("ajax_fusion_rechercher_individus"))
