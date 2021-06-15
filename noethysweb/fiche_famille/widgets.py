# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.forms.widgets import Widget
from django.template import loader
from django.utils.safestring import mark_safe
from core.utils import utils_dates


class Selection_emetteur(Widget):
    template_name = 'fiche_famille/widgets/emetteur.html'

    class Media:
        css = {"all": ("//cdnjs.cloudflare.com/ajax/libs/select2/4.0.12/css/select2.min.css",)}
        js = ("django_select2/django_select2.js", "//cdnjs.cloudflare.com/ajax/libs/select2/4.0.12/js/select2.min.js",
              "//cdnjs.cloudflare.com/ajax/libs/select2/4.0.12/js/i18n/fr.js")

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        context['choices'] = self.choices
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        if value is not None:
            context['value'] = value
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))


class Selection_mode_reglement(Widget):
    template_name = 'fiche_famille/widgets/mode_reglement.html'

    class Media:
        css = {"all": ("//cdnjs.cloudflare.com/ajax/libs/select2/4.0.12/css/select2.min.css",)}
        js = ("django_select2/django_select2.js", "//cdnjs.cloudflare.com/ajax/libs/select2/4.0.12/js/select2.min.js",
              "//cdnjs.cloudflare.com/ajax/libs/select2/4.0.12/js/i18n/fr.js")

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        context['choices'] = self.choices
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        if value is not None:
            context['value'] = value
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))


class Saisie_ventilation(Widget):
    template_name = 'fiche_famille/widgets/ventilation.html'

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



class Internet_identifiant(Widget):
    template_name = 'fiche_famille/widgets/internet_identifiant.html'

    class Media:
        js = ("lib/bootbox/bootbox.min.js",)

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


class Internet_mdp(Widget):
    template_name = 'fiche_famille/widgets/internet_mdp.html'

    class Media:
        js = ("lib/bootbox/bootbox.min.js",)

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
