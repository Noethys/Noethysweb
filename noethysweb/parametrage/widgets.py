#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.forms.widgets import Widget
from django.template import loader
from django.utils.safestring import mark_safe


class CalendrierOuvertures(Widget):
    template_name = 'parametrage/widgets/calendrier_ouvertures.html'

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


class ParametresTarifs(Widget):
    template_name = 'parametrage/widgets/parametres_tarifs.html'

    def get_context(self, name, value, attrs=None):
        from core.utils import utils_formule_tarif
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        if value is not None:
            context['value'] = value
        # Données de l'éditeur de formule : fournies par le widget lui-même, quel que soit le formulaire qui l'utilise
        context['variables_formule'] = utils_formule_tarif.VARIABLES
        context['fonctions_formule'] = utils_formule_tarif.FONCTIONS
        context['exemples_formule'] = utils_formule_tarif.EXEMPLES
        context['themes_exemples_formule'] = list(dict.fromkeys(exemple[0] for exemple in utils_formule_tarif.EXEMPLES))
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))


class Ligne_modele_planning(Widget):
    template_name = "parametrage/widgets/ligne_modele_planning.html"

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context["name"] = name
        context["value"] = value
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))


class Choix_questionnaire(Widget):
    template_name = "parametrage/widgets/choix_questionnaire.html"

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context["name"] = name
        context["value"] = value
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))
