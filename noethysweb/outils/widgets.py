#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.forms.widgets import Widget
from django.template import loader
from django.utils.safestring import mark_safe


class Pieces_jointes(Widget):
    template_name = 'outils/widgets/pieces_jointes.html'

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


class Documents_joints(Widget):
    template_name = 'outils/widgets/documents_joints.html'

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


class Texte_SMS(Widget):
    template_name = 'outils/widgets/texte_sms.html'

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


class Anomalies(Widget):
    template_name = 'core/widgets/checktree.html'
    request = None

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = name

        # Définit la hauteur du ctrl
        if "hauteur" not in context:
            context['hauteur'] = "600px"

        # Récupération des anomalies
        anomalies = context.get("anomalies", None)

        # Branches 1
        context['liste_branches1'] = [{"pk": index_categorie, "label": nom_categorie} for index_categorie, nom_categorie in enumerate(anomalies.keys())]

        # Branches 2
        context['dict_branches2'] = {}
        for index_categorie, (nom_categorie, items) in enumerate(anomalies.items()):
            context['dict_branches2'].setdefault(index_categorie, [])
            for anomalie in items:
                context['dict_branches2'][index_categorie].append({"pk": anomalie.pk, "label": anomalie.label, "checkable": anomalie.corrigeable})

        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))

    def value_from_datadict(self, data, files, name):
        selections = data.getlist(name, [])
        return ";".join(selections)
