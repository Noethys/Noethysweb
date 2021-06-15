# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views import crud
from core.models import Organisateur
from parametrage.forms.organisateur import Formulaire
from django.core.cache import cache


class Page(crud.Page):
    model = Organisateur
    url_liste = "organisateur_modifier"
    url_ajouter = "organisateur_ajouter"
    url_modifier = "organisateur_modifier"
    url_supprimer = "feries_fixes_supprimer"
    description_saisie = "Saisissez ici les informations concernant l'organisateur. Ces données seront utilisées dans les différents documents édités par Noethys."
    objet_singulier = "un organisateur"
    objet_pluriel = "de l'organisateur"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]

    def get_success_url(self):
        cache.delete('organisateur')
        return reverse_lazy("parametrage_toc")


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

