# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.forms.widgets import Widget
from django.template import loader
from django.utils.safestring import mark_safe


class ValidationApprobation(Widget):
    template_name = 'portail/widgets/validation_approbation.html'

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


class Selection_image_article(Widget):
    template_name = 'portail/widgets/selection_image_article.html'

    class Media:
        css = {"all": ("lib/select2/css/select2.min.css",)}
        js = ("django_select2/django_select2.js", "lib/select2/js/select2.min.js", "lib/select2/js/i18n/fr.js")

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
