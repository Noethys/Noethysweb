# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.forms.widgets import Widget
from django.template import loader
from django.utils.safestring import mark_safe
from core.utils import utils_dates


class CarteOSM(Widget):
    template_name = 'fiche_individu/widgets/carte_osm.html'

    class Media:
        css = {"all": ("lib/leaflet/leaflet.css",)}
        js = ("lib/leaflet/leaflet.js",)

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        if value is not None:
            context['value'] = value
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))


class SelectionForfaitsDatesWidget(Widget):
    template_name = 'core/widgets/checktree.html'

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = name

        # Définit la hauteur du ctrl
        context['hauteur'] = "300px"

        # Récupère les sélections initiales
        context['selections'] = []
        if value:
            context['selections'] = [int(id) for id in value.split(";")]

        # Importe la liste des forfaits datés disponibles
        dict_forfaits = context.get("dict_forfaits", {})

        # Branches 2
        context['dict_branches2'] = {}
        for IDactivite, activite in dict_forfaits.items():
            for tarif in getattr(activite, "tarifs", []):
                context['dict_branches2'].setdefault(IDactivite, [])
                description = "- %s " % tarif.description if tarif.description else ""
                label = "%s %s(%s - %s)" % (tarif.nom_tarif.nom, description, utils_dates.ConvertDateToFR(tarif.date_debut_forfait), utils_dates.ConvertDateToFR(tarif.date_fin_forfait))
                context['dict_branches2'][IDactivite].append({"pk": tarif.pk, "label": label})

        # Branches 1
        context['liste_branches1'] = [{"pk": IDactivite, "label": activite.nom} for IDactivite, activite in dict_forfaits.items()]

        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))

    def value_from_datadict(self, data, files, name):
        selections = data.getlist(name, [])
        return ";".join(selections)
