# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import copy
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset, Div
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import PortailChamp
from portail.utils import utils_onglets, utils_champs


class Formulaire(FormulaireBase, forms.Form):
    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'portail_parametres_renseignements_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Initialisation du layout
        self.helper.layout = Layout()
        self.helper.layout.append(Commandes(annuler_url="{% url 'parametrage_toc' %}", ajouter=False))

        # Importation des paramètres par défaut
        dict_champs = {(champ.page, champ.code): champ for champ in copy.copy(utils_champs.LISTE_CHAMPS)}
        for champ in PortailChamp.objects.all():
            for public in ("famille", "representant", "enfant", "contact"):
                if (champ.page, champ.code) in dict_champs and ((public == "famille" and "famille" in champ.page) or (public != "famille" and "individu" in champ.page)):
                    if getattr(dict_champs[(champ.page, champ.code)], public):
                        setattr(dict_champs[(champ.page, champ.code)], public, getattr(champ, public))

        # Création des fields
        for onglet in utils_onglets.LISTE_ONGLETS:
            liste_fields = []
            for champ in utils_champs.LISTE_CHAMPS:
                if champ.page == onglet.code:
                    liste_checks = []
                    for public_code, public_label in (("famille", "Famille"), ("representant", "Représentant"), ("enfant", "Enfant"), ("contact", "Contact")):
                        if getattr(champ, public_code, None) and ((public_code == "famille" and "famille" in champ.page) or (public_code != "famille" and "individu" in champ.page)):
                            code_field = "%s:%s:%s" % (champ.page, champ.code, public_code)
                            choix_etat = [("MASQUER", "Masqué"), ("AFFICHER", "Affiché"), ("MODIFIABLE", "Modifiable")]
                            if champ.choix_obligatoire:
                                choix_etat.append(("OBLIGATOIRE", "Obligatoire"))
                            self.fields[code_field] = forms.ChoiceField(label=public_label, required=False, choices=choix_etat)
                            self.fields[code_field].initial = getattr(champ, public_code)
                            liste_checks.append(Field(code_field))

                    liste_fields.append(
                        Div(
                            HTML("<label class='col-form-label col-md-3'><b>%s</b></label>" % champ.label),
                            Div(
                                Div(*liste_checks),
                                css_class="controls col-md-9"
                            ),
                            css_class="form-group row"
                        )
                    )

            self.helper.layout.append(Fieldset("<i class='fa %s margin-r-5'></i> %s" % (onglet.icone, onglet.label), *liste_fields))

        self.helper.layout.append(HTML("<br>"))
