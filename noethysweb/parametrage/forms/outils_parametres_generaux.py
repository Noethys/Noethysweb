#  Copyright (c) 2024 GIP RECIA.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Fieldset, Div, ButtonHolder
from crispy_forms.bootstrap import Field, InlineRadios
from core.utils.utils_commandes import Commandes
from core.models import PortailParametre
from core.utils.utils_parametres_generaux import LISTE_PARAMETRES


LISTE_RUBRIQUES = [
    ("Envoi emails par lots", ["emails_individus_afficher_page", "emails_familles_afficher_page", "emails_activites_afficher_page"
        ,"emails_inscriptions_afficher_page","emails_collaborateurs_afficher_page","emails_liste_diffusion_afficher_page"]),
]

class Formulaire(FormulaireBase, forms.Form):
    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'emails_parametres_form'
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Initialisation du layout
        self.helper.layout = Layout()
        self.helper.layout.append(Commandes(annuler_url="{% url 'outils_parametres_generaux' %}", ajouter=False))

        dict_parametres = {parametre.code: parametre for parametre in LISTE_PARAMETRES}
        for parametre_db in PortailParametre.objects.all():
            if parametre_db.code in dict_parametres:
                dict_parametres[parametre_db.code].From_db(parametre_db.valeur)

        # Création des fields
        for titre_rubrique, liste_parametres in LISTE_RUBRIQUES:
            liste_fields = []
            for code_parametre in liste_parametres:
                self.fields[code_parametre] = dict_parametres[code_parametre].Get_ctrl()
                self.fields[code_parametre].initial = dict_parametres[code_parametre].valeur
                liste_fields.append(Field(code_parametre))
            self.helper.layout.append(Fieldset(titre_rubrique, *liste_fields))

        self.helper.layout.append(HTML("<br>"))

        self.helper.layout.append(HTML(EXTRA_SCRIPT))

    def clean(self):
        cleaned_data = super().clean()
        emails_activites = cleaned_data.get("emails_activites")
        return cleaned_data


EXTRA_SCRIPT = """
<script>
window.onload = function() {

    console.log("Checkboxes trouvées avec succès"); // Vérifie si les cases à cocher sont trouvées

};
</script>
<br>
"""