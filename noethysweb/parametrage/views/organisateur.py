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

    def form_valid(self, form):
        self.object = form.save()

        # Recherche et enregistre les coordonnées GPS de la ville de l'organisateur
        self.object.gps = None
        if self.object.cp and self.object.ville:
            from core.utils import utils_adresse
            gps = utils_adresse.Get_gps_ville(cp=self.object.cp, ville=self.object.ville)
            if gps:
                self.object.gps = "%s;%s" % (gps["lon"], gps["lat"])
        self.object.save()

        return super().form_valid(form)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

