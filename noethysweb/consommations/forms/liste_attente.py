# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Div, ButtonHolder
from crispy_forms.bootstrap import Field
from core.widgets import DateRangePickerWidget, SelectionActivitesWidget, DateTimePickerWidget
from core.forms.base import FormulaireBase
from core.models import Consommation


class Formulaire(FormulaireBase, forms.Form):
    donnees = forms.ChoiceField(label="Données", choices=[("periode_reference", "Utiliser la période de référence"), ("periode_definie", "Utiliser les paramètres ci-dessous")], initial="periode_reference", required=False)
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget())
    activites = forms.CharField(label="Activités", required=True, widget=SelectionActivitesWidget(attrs={"afficher_colonne_detail": False}))

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        self.helper.layout = Layout(
            Field('donnees'),
            Field('periode'),
            Field('activites'),
            HTML(EXTRA_HTML),
        )

EXTRA_HTML = """
<script>

    function On_change_donnees() {
        var etat = ($('#id_donnees').val() == 'periode_reference');
        $('#div_id_periode').prop('hidden', etat);
        $('#div_id_activites').prop('hidden', etat);
    }
    $(document).ready(function() {
        $('#id_donnees').change(On_change_donnees);
        On_change_donnees.call($('#id_donnees').get(0));
    });

</script>
"""


class Formulaire_modifier_reservation(FormulaireBase, forms.Form):
    date_saisie = forms.DateTimeField(label="Date de saisie", required=True, widget=DateTimePickerWidget(attrs={"afficher_secondes": True}), help_text="Saisissez la date et heure souhaitées au format JJ/MM/AAAA HH:MM:SS")
    listeidconso = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire_modifier_reservation, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "form_modifier_reservation"
        self.helper.form_method = "post"

        # Importation des consommations de la réservation
        listeidconso = self.data.get("listeidconso", None) or self.initial.get("listeidconso", None)
        consommations = Consommation.objects.select_related("individu", "unite").filter(pk__in=[int(idconso) for idconso in listeidconso.split(";")]).order_by("unite__ordre")

        # Texte intro
        if len(consommations) == 1:
            detail = "de la consommation %s du %s" % (consommations[0].unite.nom, consommations[0].date.strftime("%d/%m/%Y"))
        else:
            detail = "des consommations %s du %s" % (" + ".join([conso.unite.nom for conso in consommations]), consommations[0].date.strftime("%d/%m/%Y"))
        texte_intro = "<p>Vous pouvez modifier ci-dessous l'heure de saisie %s pour %s. Cela vous permet notamment de modifier la position de l'individu dans la liste d'attente.</p>" % (detail, consommations[0].individu.prenom)

        # Date de saisie
        self.fields["date_saisie"].initial = min([conso.date_saisie for conso in consommations])

        self.helper.layout = Layout(
            HTML(texte_intro),
            Field("date_saisie"),
            Field("listeidconso", type="hidden"),
            ButtonHolder(
                Div(
                    HTML("""<button type="button" class="btn btn-primary" onclick="valider_modifier_reservation()"><i class="fa fa-check margin-r-5"></i>Valider</button>"""),
                    HTML("""<button type="button" class="btn btn-danger" data-dismiss="modal"><i class='fa fa-ban margin-r-5'></i>Annuler</button>"""),
                    css_class="modal-footer", style="padding-bottom:0px;padding-right:0px;"
                ),
            ),
        )

    def clean(self):
        if self.cleaned_data["date_saisie"].date() < datetime.date(2010, 1, 1):
            raise forms.ValidationError("La date saisie semble erronée")
        return self.cleaned_data
