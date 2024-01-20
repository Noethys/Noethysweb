# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.forms.widgets import Widget
from django.template import loader
from django.utils.safestring import mark_safe
from core.utils import utils_dates


class SelectionElevesWidget(Widget):
    template_name = 'core/widgets/checklist.html'

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = name

        # Récupère les sélections initiales
        context['selections'] = []
        if value:
            context['selections'] = [int(id) for id in value.split(";")]

        # Items
        context['items'] = []
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))

    def value_from_datadict(self, data, files, name):
        selections = data.getlist(name, [])
        return ";".join(selections)


class ColonnesInscritsWidget(Widget):
    template_name = 'consommations/widgets/colonnes_perso.html'

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        if value is not None:
            context['value'] = value
        else:
            context['value'] = "[]"

        # Importation du form de saisie d'une colonne
        from individus.forms.colonne_inscrits import Formulaire
        context['form'] = Formulaire()

        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))
