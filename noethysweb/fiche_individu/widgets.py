# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.
import datetime
from django.forms.widgets import Widget
from django.template import loader
from django.utils.safestring import mark_safe
from core.utils import utils_dates
from core.models import ContactUrgence, Assurance


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
        context['hauteur'] = "500px"

        # Récupère les sélections initiales
        context['selections'] = []
        if value:
            context['selections'] = [int(id) for id in value.split(";")]

        # Importe la liste des forfaits datés disponibles
        dict_forfaits = context.get("dict_forfaits", {})

        # Branches 2
        context['dict_branches2'] = {}
        for IDactivite, activite in dict_forfaits.items():
            tarifs = sorted(getattr(activite, "tarifs", []), key=lambda x: x.nom_tarif.nom)
            for tarif in tarifs:
                context['dict_branches2'].setdefault(IDactivite, [])
                description = "- %s " % tarif.description if tarif.description else ""
                if tarif.date_debut_forfait and tarif.date_fin_forfait:
                    label = "%s %s(%s - %s)" % (tarif.nom_tarif.nom, description, utils_dates.ConvertDateToFR(tarif.date_debut_forfait), utils_dates.ConvertDateToFR(tarif.date_fin_forfait))
                else:
                    label = "%s %s" % (tarif.nom_tarif.nom, description)
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


class SelectionContactsAutresFiches(Widget):
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

        # Récupération des dates
        idfamille = context.get("idfamille", None)
        idindividu = context.get("idindividu", None)

        # Importation des contacts
        contacts = ContactUrgence.objects.select_related("individu").exclude(individu_id=idindividu).filter(famille_id=idfamille).order_by("nom", "prenom")
        dict_contacts = {}
        for contact in contacts:
            dict_contacts.setdefault(contact.individu, [])
            dict_contacts[contact.individu].append(contact)

        # Branches 1
        context['liste_branches1'] = [{"pk": individu.pk, "label": individu.Get_nom()} for individu, contacts in dict_contacts.items()]

        # Branches 2
        context['dict_branches2'] = {}
        for individu, contacts in dict_contacts.items():
            context['dict_branches2'].setdefault(individu.pk, [])
            for contact in contacts:
                context['dict_branches2'][individu.pk].append({"pk": contact.pk, "label": contact.Get_nom()})

        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))

    def value_from_datadict(self, data, files, name):
        selections = data.getlist(name, [])
        return ";".join(selections)

class Internet_identifiant(Widget):
    template_name = 'fiche_individu/widgets/internet_identifiant.html'

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
    template_name = 'fiche_individu/widgets/internet_mdp.html'

    class Media:
        js = ("lib/bootbox/bootbox.min.js",)

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        context['maintenant'] = datetime.datetime.now()
        if value is not None:
            context['value'] = value
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))


class SelectionAssurancesAutresFiches(Widget):
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

        # Récupération des dates
        idfamille = context.get("idfamille", None)
        idindividu = context.get("idindividu", None)

        # Importation des assurances
        assurances = Assurance.objects.select_related("individu").exclude(individu_id=idindividu).filter(famille_id=idfamille).order_by("-date_debut")
        dict_assurances = {}
        for assurance in assurances:
            dict_assurances.setdefault(assurance.individu, [])
            dict_assurances[assurance.individu].append(assurance)

        # Branches 1
        context['liste_branches1'] = [{"pk": individu.pk, "label": individu.Get_nom()} for individu, assurances in dict_assurances.items()]

        # Branches 2
        context['dict_branches2'] = {}
        for individu, assurances in dict_assurances.items():
            context['dict_branches2'].setdefault(individu.pk, [])
            for assurance in assurances:
                context['dict_branches2'][individu.pk].append({"pk": assurance.pk, "label": str(assurance)})

        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))

    def value_from_datadict(self, data, files, name):
        selections = data.getlist(name, [])
        return ";".join(selections)
