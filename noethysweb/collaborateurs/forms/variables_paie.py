# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, decimal
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.forms.select2 import Select2MultipleWidget
from core.models import GroupeCollaborateurs
from collaborateurs.forms.planning_absences import Get_choix_mois


def Get_mois_defaut():
    """ Mois précédent jusqu'au 10 du mois (préparation de la paie), mois en cours ensuite """
    aujourdhui = datetime.date.today()
    if aujourdhui.day <= 10:
        aujourdhui = aujourdhui.replace(day=1) - datetime.timedelta(days=1)
    return aujourdhui.strftime("%Y-%m")


class Formulaire(FormulaireBase, forms.Form):
    mois = forms.ChoiceField(label="Mois", choices=[], required=True)
    groupes = forms.ModelMultipleChoiceField(label="Groupes de collaborateurs", queryset=GroupeCollaborateurs.objects.all().order_by("nom"), required=False,
                                             widget=Select2MultipleWidget({"data-minimum-input-length": 0}), help_text="Laissez vide pour tous les collaborateurs.")
    donnees = forms.ChoiceField(label="Heures retenues", choices=[("REALISE", "Réalisé si saisi, sinon planifié"), ("PLANIFIE", "Planifié")], initial="REALISE", required=True)
    duree_legale = forms.DecimalField(label="Durée légale hebdomadaire (h)", initial=decimal.Decimal("35"), min_value=1, max_value=60, decimal_places=2, required=True,
                                      help_text="Seuil entre temps partiel (heures complémentaires) et temps plein (heures supplémentaires).")
    rattachement = forms.ChoiceField(label="Semaines à cheval sur deux mois", choices=[("FIN", "Rattachées au mois de leur dimanche"), ("DEBUT", "Rattachées au mois de leur lundi")],
                                     initial="FIN", required=True, help_text="Les heures complémentaires et supplémentaires sont calculées par semaine civile.")
    format_heures = forms.ChoiceField(label="Format des heures dans Excel", choices=[("DECIMAL", "Décimal (7,50)"), ("HEURES", "Heures et minutes (7:30)")], initial="DECIMAL", required=True)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "form_parametres"
        self.helper.form_method = "post"
        self.fields["mois"].choices = Get_choix_mois(nbre_avant=36, nbre_apres=2)
        self.fields["mois"].initial = Get_mois_defaut()

        self.helper.layout = Layout(
            Field("mois"),
            Field("groupes"),
            Field("donnees"),
            Field("duree_legale"),
            Field("rattachement"),
            Field("format_heures"),
        )
