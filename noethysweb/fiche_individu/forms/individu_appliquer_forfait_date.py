# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Fieldset, Div, ButtonHolder, Field
from core.utils.utils_commandes import Commandes
from fiche_individu.widgets import SelectionForfaitsDatesWidget
from individus.utils import utils_forfaits
from core.models import Inscription
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    action = forms.CharField(label="Action", required=False)
    forfaits = forms.CharField(label="Forfaits disponibles", required=False, widget=SelectionForfaitsDatesWidget(attrs={"coche_tout": False}))
    afficher_forfaits_obsoletes = forms.BooleanField(label="Afficher les forfaits obsolètes", required=False, initial=False)

    def __init__(self, *args, **kwargs):
        self.idfamille = kwargs.pop("idfamille")
        self.idindividu = kwargs.pop("idindividu")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_forfaits_form'
        self.helper.form_method = 'post'

        # Récupère variable masquer_forfaits_obsoletes
        afficher_forfaits_obsoletes = True if self.data.get("afficher_forfaits_obsoletes") == "on" else False

        # Importe la liste des forfaits datés disponibles
        activites = [inscription.activite_id for inscription in Inscription.objects.filter(famille=self.idfamille, individu=self.idindividu)]
        f = utils_forfaits.Forfaits(famille=self.idfamille, activites=activites, individus=[self.idindividu], saisie_manuelle=True, saisie_auto=False)
        dict_forfaits = f.GetForfaits(masquer_forfaits_obsoletes=not afficher_forfaits_obsoletes)

        self.fields['forfaits'].widget.attrs.update({'dict_forfaits': dict_forfaits})
        self.fields['forfaits'].label = False

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'individu_inscriptions_liste' idfamille=idfamille idindividu=idindividu %}", ajouter=False, enregistrer_label="<i class='fa fa-check margin-r-5'></i>Appliquer les forfaits cochés"),
            Hidden('action', value=''),
            Field("forfaits"),
            Field("afficher_forfaits_obsoletes"),
            HTML(EXTRA_HTML),
        )


EXTRA_HTML = """
<script>
    $(document).ready(function() {
        $("#id_afficher_forfaits_obsoletes").on("change", function (event) {
            $("[name=action]").val("afficher_forfaits_obsoletes");
            $("[name=submit]").click();
        });
    });
</script>
"""