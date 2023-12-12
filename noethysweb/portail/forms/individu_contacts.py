# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Fieldset
from crispy_forms.bootstrap import Field
from core.models import ContactUrgence
from core.widgets import Telephone, CodePostal, Ville
from core.utils.utils_commandes import Commandes
from portail.forms.fiche import FormulaireBase


class Formulaire(FormulaireBase, ModelForm):

    class Meta:
        model = ContactUrgence
        fields = "__all__"
        widgets = {
            'tel_domicile': Telephone(),
            'tel_mobile': Telephone(),
            'tel_travail': Telephone(),
            'rue_resid': forms.Textarea(attrs={'rows': 2}),
            'cp_resid': CodePostal(attrs={"id_ville": "id_ville_resid"}),
            'ville_resid': Ville(attrs={"id_codepostal": "id_cp_resid"}),
            'observations': forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            "nom": _("Saisissez le nom de famille en majuscules."),
            "prenom": _("Saisissez le prénom en minuscules avec la première lettre majuscule."),
            "lien": _("Précisez le lien avec l'individu. Exemples : frère, voisin, tante, ami de la famille..."),
            "cp_resid": _("Saisissez le code postal, patientez une seconde et sélectionnez la ville dans la liste déroulante."),
            "ville_resid": _("Saisissez le nom de la ville, patientez une seconde et sélectionnez la ville dans la liste déroulante."),
        }

    def __init__(self, *args, **kwargs):
        rattachement = kwargs.pop("rattachement", None)
        mode = kwargs.pop("mode", "MODIFICATION")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_contacts_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'
        # self.helper.use_custom_control = False

        # Ajoute le prénom de l'individu dans le label du lien
        self.fields["lien"].label = "Lien avec %s" % rattachement.individu.prenom

        # Affichage
        self.helper.layout = Layout(
            Hidden('famille', value=rattachement.famille_id),
            Hidden('individu', value=rattachement.individu_id),
            Fieldset(_("Identité"),
                Field("nom"),
                Field("prenom"),
                Field("lien"),
            ),
            Fieldset(_("Adresse de résidence"),
                Field("rue_resid"),
                Field("cp_resid"),
                Field("ville_resid"),
            ),
            Fieldset(_("Coordonnées"),
                Field("tel_domicile"),
                Field("tel_mobile"),
                Field("tel_travail"),
                Field("mail"),
            ),
            Fieldset(_("Autorisations"),
                Field("autorisation_sortie"),
                Field("autorisation_appel"),
            ),
            Fieldset(_("Divers"),
                Field("observations"),
            ),
            Commandes(annuler_url="{% url 'portail_individu_contacts' idrattachement=rattachement.pk %}", aide=False, ajouter=False, css_class="pull-right"),
        )
