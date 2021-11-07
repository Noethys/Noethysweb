# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from fiche_individu.widgets import SelectionContactsAutresFiches


class Formulaire(FormulaireBase, forms.Form):
    contacts = forms.CharField(label="Contacts disponibles", required=False, widget=SelectionContactsAutresFiches(attrs={"coche_tout": False}))

    def __init__(self, *args, **kwargs):
        self.idfamille = kwargs.pop("idfamille")
        self.idindividu = kwargs.pop("idindividu")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_contacts_importer_form'
        self.helper.form_method = 'post'

        # Envoie les idfamille et idindividu au widget checktree
        self.fields['contacts'].widget.attrs.update({"idfamille": self.idfamille, "idindividu": self.idindividu})
        self.fields['contacts'].label = False

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'individu_contacts_liste' idfamille=idfamille idindividu=idindividu %}", ajouter=False, enregistrer_label="<i class='fa fa-check margin-r-5'></i>Importer les contacts cochés"),
            Field("contacts"),
        )
