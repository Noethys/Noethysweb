#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.forms.widgets import Widget
from django.template import loader
from django.utils.safestring import mark_safe



class Cotisations_depot(Widget):
    template_name = 'cotisations/widgets/cotisations_depot.html'

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


class Selection_beneficiaires_cotisation(Widget):
    template_name = 'cotisations/widgets/selection_beneficiaires_cotisation.html'

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


def Get_types_cotisations_accessibles(request=None):
    """ Renvoie les types d'adhésions accessibles à l'utilisateur """
    from django.db.models import Q
    from core.models import TypeCotisation
    condition_structure = Q(structure__isnull=True)
    if request:
        condition_structure |= Q(structure__in=request.user.structures.all())
    return TypeCotisation.objects.filter(condition_structure).order_by("nom")


class SelectionTypesCotisationsWidget(Widget):
    """ Liste à cocher des types d'adhésions (utilisée par les filtres de listes) """
    template_name = 'core/widgets/checklist.html'
    request = None

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = self.attrs.get("name", name)

        # Récupère les sélections initiales
        context['selections'] = []
        if value:
            value = value.replace("types_cotisations:", "")
            context['selections'] = [int(id) for id in value.split(";") if id]
            context['coche_tout'] = False

        # Items
        context['items'] = [{"pk": type_cotisation.pk, "label": type_cotisation.nom} for type_cotisation in Get_types_cotisations_accessibles(self.request)]
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))

    def value_from_datadict(self, data, files, name):
        selections = data.getlist(name, [])
        return ";".join(selections)


class SelectionUnitesCotisationsWidget(Widget):
    """ Arborescence à cocher types d'adhésions > unités d'adhésion (utilisée par les filtres de listes) """
    template_name = 'core/widgets/checktree.html'
    request = None

    def get_context(self, name, value, attrs=None):
        from core.models import UniteCotisation
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = self.attrs.get("name", name)

        # Récupère les sélections initiales
        context['selections'] = []
        if value:
            value = value.replace("unites_cotisations:", "")
            context['selections'] = [int(id) for id in value.split(";") if id]
            context['coche_tout'] = False

        # Branches 1 : types d'adhésions
        types_cotisations = list(Get_types_cotisations_accessibles(self.request))
        context['liste_branches1'] = [{"pk": type_cotisation.pk, "label": type_cotisation.nom} for type_cotisation in types_cotisations]

        # Branches 2 : unités d'adhésion
        context['dict_branches2'] = {}
        for unite in UniteCotisation.objects.filter(type_cotisation__in=types_cotisations).order_by("date_debut", "nom"):
            label = unite.nom
            if unite.date_debut and unite.date_fin:
                label += " (%s - %s)" % (unite.date_debut.strftime("%d/%m/%Y"), unite.date_fin.strftime("%d/%m/%Y"))
            context['dict_branches2'].setdefault(unite.type_cotisation_id, [])
            context['dict_branches2'][unite.type_cotisation_id].append({"pk": unite.pk, "label": label})

        # Retire les types sans unité
        context['liste_branches1'] = [branche for branche in context['liste_branches1'] if branche["pk"] in context['dict_branches2']]
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))

    def value_from_datadict(self, data, files, name):
        selections = data.getlist(name, [])
        return ";".join(selections)
