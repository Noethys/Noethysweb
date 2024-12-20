# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, json
from django.forms.utils import flatatt
from django.forms.widgets import Widget, Textarea, ClearableFileInput, FileInput, SelectMultiple
from django.template import loader
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.conf import settings
from crispy_forms.layout import LayoutObject, TEMPLATE_PACK
from core.utils import utils_dates
from core.models import Activite, TypeGroupeActivite, Groupe, Organisateur


class DatePickerWidget(Widget):
    template_name = 'core/widgets/datepicker.html'

    class Media:
        css = {"all": ("lib/datepicker/css/bootstrap-datepicker3.min.css",)}
        js = ("lib/datepicker/js/bootstrap-datepicker.min.js", "lib/datepicker/locales/bootstrap-datepicker.fr.min.js", "lib/moment/moment.min.js")

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = name

        try:
            value = utils_dates.ConvertDateToFR(value)
        except:
            pass

        if value and context.get("multidate", False):
            if ";" in value:
                context['dates'] = value.split(";")
            else:
                context['dates'] = [str(utils_dates.ConvertDateToDate(value)),]

        if value is not None:
            if isinstance(value, str) and len(value) == 10:
                value = datetime.datetime.strptime(value, "%d/%m/%Y")
            context['value'] = value

        if 'format' not in context:
            context['format'] = 'dd/mm/yyyy'
        context['djformat'] = settings.DATE_FORMAT
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))

    def value_from_datadict(self, data, files, name):
        date_str = data.get(name, None)
        if date_str:
            if ";" in date_str:
                return date_str
            if "/" in date_str:
                return utils_dates.ConvertDateFRtoDate(date_str)
            if "-" in date_str:
                return utils_dates.ConvertDateENGtoDate(date_str)
        return None


class MonthPickerWidget(Widget):
    template_name = 'core/widgets/monthpicker.html'

    class Media:
        css = {"all": ("lib/datepicker/css/bootstrap-datepicker3.min.css",)}
        js = ("lib/datepicker/js/bootstrap-datepicker.min.js", "lib/datepicker/locales/bootstrap-datepicker.fr.min.js")

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        if value is not None:
            context['value'] = value
        context['djformat'] = settings.DATE_FORMAT
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))


class TimePickerWidget(Widget):
    template_name = 'core/widgets/timepicker.html'

    class Media:
        css = {"all": ("lib/timepicker/bootstrap-timepicker.min.css",)}
        js = ("lib/timepicker/bootstrap-timepicker.min.js",)

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        if value is not None:
            context['value'] = value
        if 'format' not in context:
            context['format'] = 'HH:ii P'
        context['djformat'] = settings.TIME_FORMAT
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))


class DateTimePickerWidget(Widget):
    template_name = 'core/widgets/datetimepicker.html'

    class Media:
        css = {"all": ("lib/datetimepicker/css/bootstrap-datetimepicker.min.css",)}
        js = ("lib/datetimepicker/js/bootstrap-datetimepicker.min.js", "lib/datetimepicker/js/locales/bootstrap-datetimepicker.fr.js")

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        if value is not None:
            context['value'] = value
        if 'format' not in context:
            context['format'] = 'dd/mm/yyyy hh:ii'
        if context.get("afficher_secondes", False):
            context['format'] = 'dd/mm/yyyy hh:ii:ss'
        context['djformat'] = settings.DATETIME_FORMAT
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))

    def value_from_datadict(self, data, files, name):
        date = data.get(name, None)
        if not date:
            return None
        format = "%d/%m/%Y %H:%M:%S" if len(date) == 19 else "%d/%m/%Y %H:%M"
        date = datetime.datetime.strptime(date, format)
        return date


class ColorPickerWidget(Widget):
    template_name = 'core/widgets/colorpicker.html'

    class Media:
        css = {"all": ("lib/colorpicker/bootstrap-colorpicker.min.css",)}
        js = ("lib/colorpicker/bootstrap-colorpicker.min.js",)

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


class CKEditorWidget(Textarea):

    template_name = 'core/widgets/ckeditor.html'

    def get_context(self, name, value, attrs=None):
        self.attrs['flatatt'] = flatatt(self.attrs)
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



class Telephone(Widget):
    template_name = 'core/widgets/telephone.html'

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        if value is not None:
            context['value'] = value
        context["TELEPHONE_FORMAT_FR"] = settings.TELEPHONE_FORMAT_FR
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))


class DateMask(Widget):
    template_name = 'core/widgets/date_mask.html'

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


class Rue(Widget):
    template_name = 'core/widgets/rue.html'

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context["name"] = name
        if value is not None:
            context["value"] = value
        # Récupération des coordonnées GPS de l'organisateur pour une meilleure précision des réponses de l'API adresse
        from core.utils import utils_adresse
        context["gps_organisateur"] = utils_adresse.Get_gps_organisateur()
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))


class Ville(Widget):
    template_name = 'core/widgets/ville.html'

    # class Media:
    #     js = ("lib/jqueryui/jquery-ui.min.js",)

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


class CodePostal(Widget):
    template_name = 'core/widgets/codepostal.html'

    # class Media:
    #     js = ("lib/jqueryui/jquery-ui.min.js",)

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


class Formset(LayoutObject):
    template = "core/widgets/formset.html"

    def __init__(self, formset_name_in_context, template=None):
        self.formset_name_in_context = formset_name_in_context
        self.fields = []
        if template:
            self.template = template

    def render(self, *args, **kwargs):
        """ Arguments ci-dessus différents selon versions de crispy :
        avec django-crispy-forms 1.x : form, form_style, context, template_pack=TEMPLATE_PACK
        avec django-crispy-forms 2.x : form, context, template_pack=TEMPLATE_PACK
        """
        context = args[-1]
        formset = context[self.formset_name_in_context]
        return render_to_string(self.template, {'formset': formset})


class SliderWidget(Widget):
    template_name = 'core/widgets/slider.html'

    class Media:
        css = {"all": ("lib/bootstrap-slider/css/bootstrap-slider.min.css",)}
        js = ("lib/bootstrap-slider/bootstrap-slider.min.js",)

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


class Select_avec_commandes(Widget):
    template_name = 'core/widgets/select_avec_commandes.html'

    class Media:
        css = {"all": ("lib/select2/css/select2.min.css",)}
        js = ("django_select2/django_select2.js", "lib/select2/js/select2.min.js", "lib/select2/js/i18n/fr.js")

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        context['choices'] = self.choices
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        if value:
            context['value'] = int(value)
        if "donnees_extra" not in context:
            context['donnees_extra'] = {}
        context['donnees_extra'] = json.dumps(context['donnees_extra'])
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))


class Select_avec_commandes_form(Widget):
    template_name = 'core/widgets/select_avec_commandes_form.html'

    class Media:
        css = {"all": ("lib/select2/css/select2.min.css",)}
        js = ("django_select2/django_select2.js", "lib/select2/js/select2.min.js", "lib/select2/js/i18n/fr.js",
              "lib/bootbox/bootbox.min.js")

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        context['choices'] = self.choices
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        if value:
            context['value'] = int(value)
        if "donnees_extra" not in context:
            context['donnees_extra'] = {}
        if "afficher_bouton_ajouter" not in context:
            context['afficher_bouton_ajouter'] = True
        context['donnees_extra'] = json.dumps(context['donnees_extra'])
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))


class Select_avec_commandes_advanced(Widget):
    template_name = 'core/widgets/select_avec_commandes_advanced.html'

    class Media:
        css = {"all": ("lib/select2/css/select2.min.css",)}
        js = ("django_select2/django_select2.js", "lib/select2/js/select2.min.js", "lib/select2/js/i18n/fr.js",
              "lib/bootbox/bootbox.min.js")

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        context['choices'] = self.choices
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        if value:
            context['value'] = int(value)
        if "donnees_extra" not in context:
            context['donnees_extra'] = {}
        if "afficher_bouton_ajouter" not in context:
            context['afficher_bouton_ajouter'] = True
        context['donnees_extra'] = json.dumps(context['donnees_extra'])
        context["url_ajax"] = "ajax_select_avec_commandes_advanced"
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))


class Select_many_avec_plus(SelectMultiple):
    template_name = 'core/widgets/select_many_avec_plus.html'

    class Media:
        css = {"all": ("lib/select2/css/select2.min.css",)}
        js = ("django_select2/django_select2.js", "lib/select2/js/select2.min.js", "lib/select2/js/i18n/fr.js",
              "lib/bootbox/bootbox.min.js")

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        context['choices'] = self.choices
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        context['selections'] = value
        if "donnees_extra" not in context:
            context['donnees_extra'] = {}
        if "afficher_bouton_ajouter" not in context:
            context['afficher_bouton_ajouter'] = True
        context['donnees_extra'] = json.dumps(context['donnees_extra'])
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))



class DateRangePickerWidget(Widget):
    template_name = 'core/widgets/daterangepicker.html'

    class Media:
        css = {"all": ("lib/daterangepicker/daterangepicker.css",)}
        js = ("lib/moment/moment.min.js", "lib/daterangepicker/daterangepicker.js")

    def get_context(self, name, value, attrs=None):
        if value and ";" in value:
            date_debut, date_fin = value.split(";")
            date_debut = utils_dates.ConvertDateToFR(date_debut)
            date_fin = utils_dates.ConvertDateToFR(date_fin)
            value = "%s - %s" % (date_debut, date_fin)
        context = dict(self.attrs.items())
        attrs["auto_application"] = "true" if attrs.get("auto_application", False) else "false"
        attrs["afficher_periodes_predefinies"] = attrs.get("afficher_periodes_predefinies", True)
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        if value is not None:
            context['value'] = value
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))

    def value_from_datadict(self, data, files, name):
        """ Convertit la période de datesfr en date python """
        try:
            periodestr = data.get(name)
            date_debut, date_fin = periodestr.split("-")
            date_debut = utils_dates.ConvertDateFRtoDate(date_debut)
            date_fin = utils_dates.ConvertDateFRtoDate(date_fin)
            return "%s;%s" % (date_debut, date_fin)
        except:
            return None



class SelectionActivitesWidget(Widget):
    template_name = 'core/widgets/selection_activites.html'
    request = None

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        context['id'] = attrs.get("id", 0)
        context['selection'] = {"type": "groupes_activites", "ids": []}
        context.setdefault('afficher_colonne_detail', True)
        if value:
            try:
                # Si la valeur importée est un JSON
                context['selection'] = json.loads(value)
            except:
                # Si la valeur importée est un str
                if ":" in value:
                    type_selection, valeurs = value.split(":")
                    context['selection'] = {"type": type_selection, "ids": [int(x) for x in valeurs.split(";")]}

        context['groupes_activites'] = TypeGroupeActivite.objects.filter(structure__in=self.request.user.structures.all()).order_by("nom")
        context['activites'] = Activite.objects.filter(structure__in=self.request.user.structures.all()).order_by("-date_fin", "nom")
        if context.get("afficher_groupes", False):
            context['groupes'] = {}
            for groupe in Groupe.objects.select_related('activite').filter(activite__structure__in=self.request.user.structures.all()).order_by("ordre"):
                context['groupes'].setdefault(groupe.activite, [])
                context['groupes'][groupe.activite].append(groupe)
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))

    def value_from_datadict(self, data, files, name):
        if isinstance(data, list):
            choix_activites = None
            dict_valeurs = {}
            for dict_temp in data:
                if dict_temp["name"] == "choix_activites":
                    choix_activites = dict_temp["value"]
                if dict_temp["name"] in ["liste_groupes_activites", "liste_activites", "liste_groupes"]:
                    dict_valeurs.setdefault(dict_temp["name"].replace("liste_", ""), [])
                    dict_valeurs[dict_temp["name"].replace("liste_", "")].append(int(dict_temp["value"]))
            return json.dumps({"type": choix_activites, "ids": dict_valeurs.get(choix_activites, [])})
        else:
            if data.get("choix_activites") == "groupes_activites":
                return json.dumps({"type": "groupes_activites", "ids": [int(x) for x in data.getlist("liste_groupes_activites", [])]})
            if data.get("choix_activites") == "activites":
                return json.dumps({"type": "activites", "ids": [int(x) for x in data.getlist("liste_activites", [])]})
            if data.get("choix_activites") == "groupes":
                return json.dumps({"type": "groupes", "ids": [int(x) for x in data.getlist("liste_groupes", [])]})


class CheckDateWidget(Widget):
    template_name = 'core/widgets/checkdate.html'

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        if value is not None:
            context['value'] = value
            etat = ""
        else:
            etat = "disabled"
        id = attrs.get("id")
        widget_date = DatePickerWidget(attrs={"id": id, "class": "datepickerwidget check_date", "disabled": etat})
        context['widget_date'] = widget_date.render(name=name, value=value)
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))


# class CheckDateRangePickerWidget(Widget):
#     template_name = 'core/widgets/checkdaterangepicker.html'
#
#     class Media:
#         css = {"all": ("lib/daterangepicker/daterangepicker.css",)}
#         js = ("lib/moment/moment.min.js", "lib/daterangepicker/daterangepicker.js")
#
#     def get_context(self, name, value, attrs=None):
#         context = dict(self.attrs.items())
#         if attrs is not None:
#             context.update(attrs)
#         context['name'] = name
#         if value is not None:
#             context['value'] = value
#             etat = ""
#         else:
#             etat = "disabled"
#         id = attrs.get("id")
#         widget_date = DateRangePickerWidget(attrs={"id": id, "class": "daterangepickerwidget check_date form-control", "disabled": etat})
#         context['widget_date'] = widget_date.render(name=name, value=value)
#         return context
#
#     def render(self, name, value, attrs=None, renderer=None):
#         context = self.get_context(name, value, attrs)
#         return mark_safe(loader.render_to_string(self.template_name, context))
#
#     def value_from_datadict(self, data, files, name):
#         """ Convertit la période de datesfr en date python """
#         try:
#             periodestr = data.get(name)
#             date_debut, date_fin = periodestr.split("-")
#             date_debut = utils_dates.ConvertDateFRtoDate(date_debut)
#             date_fin = utils_dates.ConvertDateFRtoDate(date_fin)
#             return "%s;%s" % (date_debut, date_fin)
#         except:
#             return None


class FormIntegreWidget(Widget):
    template_name = 'core/widgets/form_integre.html'

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        if value is not None:
            context['value'] = value
        if "hauteur" not in context:
            context["hauteur"] = 200
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))


class Profil_configuration(Widget):
    template_name = 'core/widgets/profil_configuration.html'
    request = None

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        context['choices'] = self.choices
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        if value:
            context['value'] = int(value)
        if "donnees_extra" not in context:
            context['donnees_extra'] = {}
        context['donnees_extra'] = json.dumps(context['donnees_extra'])
        context['structures'] = self.request.user.structures.all().order_by("nom")
        from core.forms.profil_configuration import Formulaire as Form_profil
        context['form_profil'] = Form_profil(request=self.request)
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))


class Selection_image(ClearableFileInput):
    template_name = 'core/widgets/selection_image.html'

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        if value is not None:
            context['value'] = value
        if "masquer_image" not in context:
            context["masquer_image"] = False
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))



class Crop_image(ClearableFileInput):
    template_name = 'core/widgets/crop_image.html'

    class Media:
        css = {"all": ("lib/cropper/cropper.min.css",)}
        js = ("lib/cropper/cropper.min.js",)

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


class Selection_fichier(FileInput):
    template_name = 'core/widgets/selection_fichier.html'

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


class Select_activite(Widget):
    template_name = 'core/widgets/select_activite.html'

    class Media:
        css = {"all": ("lib/select2/css/select2.min.css",)}
        js = ("django_select2/django_select2.js", "lib/select2/js/select2.min.js", "lib/select2/js/i18n/fr.js")

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if "request" in self.attrs:
            context["activites"] = Activite.objects.filter(structure__in=self.attrs["request"].user.structures.all()).order_by("-date_fin", "nom")
        else:
            context["activites"] = []
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        if value:
            context['value'] = int(value)
        if "afficher_tout" not in context:
            context['afficher_tout'] = False
        if "donnees_extra" not in context:
            context['donnees_extra'] = {}
        context['donnees_extra'] = json.dumps(context['donnees_extra'])
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))


class Selection_avec_icone(Widget):
    template_name = "core/widgets/selection_avec_icone.html"

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

    def value_from_datadict(self, data, files, name):
        valeur = data.get(name)
        if valeur == "None": return None
        return valeur
