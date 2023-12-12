# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.utils.translation import gettext as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.models import Assurance
from fiche_individu.widgets import SelectionAssurancesAutresFiches


class Formulaire(FormulaireBase, forms.Form):
    assurances = forms.CharField(label=_("Assurances disponibles"), required=False, widget=SelectionAssurancesAutresFiches(
        attrs={"texte_si_vide": _("Aucune assurance disponible"), "hauteur_libre": True, "coche_tout": False}))

    def __init__(self, *args, **kwargs):
        self.idfamille = kwargs.pop("idfamille")
        self.idindividu = kwargs.pop("idindividu")
        self.idrattachement = kwargs.pop("idrattachement")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_assurances_importer_form'
        self.helper.form_method = 'post'

        # Envoie les idfamille et idindividu au widget checktree
        self.fields['assurances'].widget.attrs.update({"idfamille": self.idfamille, "idindividu": self.idindividu})
        self.fields['assurances'].label = False

        # Vérifie s'il existe des assurances à importer
        if Assurance.objects.exclude(individu_id=self.idindividu).filter(famille_id=self.idfamille):
            html = """
                <div class="pull-right">
                    <button type="submit" class='btn btn-primary' name="enregistrer"><i class="fa fa-check margin-r-5"></i>{label1}</button> 
                    <a class="btn btn-danger" href="{{% url 'portail_individu_assurances' idrattachement=idrattachement %}}" title="{title}"><i class="fa fa-ban margin-r-5"></i>{label2}</a>
                </div>
            """.format(label1=_("Importer les assurances cochées"), title=_("Annuler"), label2=_("Annuler"))
        else:
            html = """
                <div class="pull-right">
                    <a class="btn btn-danger" href="{{% url 'portail_individu_assurances' idrattachement=idrattachement %}}" title="{title}"><i class="fa fa-ban margin-r-5"></i>{label}</a>
                </div>
            """.format(title=_("Annuler"), label=_("Annuler"))

        # Affichage
        self.helper.layout = Layout(
            Field("assurances"),
            HTML(html),
        )
