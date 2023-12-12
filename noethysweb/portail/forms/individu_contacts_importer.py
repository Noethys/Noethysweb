# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.models import ContactUrgence
from fiche_individu.widgets import SelectionContactsAutresFiches


class Formulaire(FormulaireBase, forms.Form):
    contacts = forms.CharField(label=_("Contacts disponibles"), required=False, widget=SelectionContactsAutresFiches(
        attrs={"texte_si_vide": _("Aucun contact disponible"), "hauteur_libre": True, "coche_tout": False}))

    def __init__(self, *args, **kwargs):
        self.idfamille = kwargs.pop("idfamille")
        self.idindividu = kwargs.pop("idindividu")
        self.idrattachement = kwargs.pop("idrattachement")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_contacts_importer_form'
        self.helper.form_method = 'post'

        # Envoie les idfamille et idindividu au widget checktree
        self.fields['contacts'].widget.attrs.update({"idfamille": self.idfamille, "idindividu": self.idindividu})
        self.fields['contacts'].label = False

        # Vérifie s'il existe des contacts à importer
        if ContactUrgence.objects.exclude(individu_id=self.idindividu).filter(famille_id=self.idfamille):
            html = """
                <div class="pull-right">
                    <button type="submit" class='btn btn-primary' name="enregistrer"><i class="fa fa-check margin-r-5"></i>{label}</button> 
                    <a class="btn btn-danger" href="{{% url 'portail_individu_contacts' idrattachement=idrattachement %}}" title="{annuler}"><i class="fa fa-ban margin-r-5"></i>{annuler}</a>
                </div>
            """.format(label=_("Importer les contacts cochés"), annuler=_("Annuler"))
        else:
            html = """
                <div class="pull-right">
                    <a class="btn btn-danger" href="{{% url 'portail_individu_contacts' idrattachement=idrattachement %}}" title="{label}"><i class="fa fa-ban margin-r-5"></i>{label}</a>
                </div>
            """.format(label=_("Annuler"))

        # Affichage
        self.helper.layout = Layout(
            Field("contacts"),
            HTML(html),
        )
