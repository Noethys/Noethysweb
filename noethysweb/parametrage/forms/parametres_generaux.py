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
    ("Compte Utilisateurs", ["compte_famille", "compte_individu"]),

    ("Fiche Individu", ["questionnaire_afficher_page_individu" , "liens_afficher_page_individu", "regimes_alimentaires_afficher_page_individu",
             "maladies_afficher_page_individu" ,"medical_afficher_page_individu" , "assurances_afficher_page_individu" , "contacts_afficher_page_individu" ,
             "transports_afficher_page_individu" , "consommations_afficher_page_individu"]),

    ("Fiche Famille", ["questionnaire_afficher_page_famille" , "pieces_afficher_page_famille" , "locations_afficher_page_famille" ,
            "cotisations_afficher_page_famille" , "caisse_afficher_page_famille" , "aides_afficher_page_famille" , "quotients_afficher_page_famille" ,
            "prestations_afficher_page_famille" , "factures_afficher_page_famille" , "reglements_afficher_page_famille" ,
            "messagerie_afficher_page_famille" , "outils_afficher_page_famille" , "consommations_afficher_page_famille"]),

    ("Portail Utilisateur", [
        "outils_afficher_page_portailuser" ,"locations_afficher_page_portailuser" , "adhesions_afficher_page_portailuser" ,
            "consommations_afficher_page" ,"factures_afficher_page_portailuser" , "reglements_afficher_page_portailuser"
            , "comptabilite_afficher_page_portailuser" ,"collabotrateurs_afficher_page_portailuser" , "aides_afficher_page_portailuser"])

]


class Formulaire(FormulaireBase, forms.Form):
    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'compte_parametres_form'
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Initialisation du layout
        self.helper.layout = Layout()
        self.helper.layout.append(Commandes(annuler_url="{% url 'parametres_generaux' %}", ajouter=False))

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
        compte_individu = cleaned_data.get("compte_individu")
        compte_famille = cleaned_data.get("compte_famille")
        # Validation pour s'assurer qu'un seul champ est sélectionné
        if compte_individu and compte_famille:
            raise forms.ValidationError("Vous ne pouvez sélectionner qu'un seul compte à la fois.")
        return cleaned_data


EXTRA_SCRIPT = """
<script>
window.onload = function() {
    const checkboxIndividu = document.getElementById("id_compte_individu"); 
    const checkboxFamille = document.getElementById("id_compte_famille");  

    console.log("Checkboxes trouvées avec succès"); // Vérifie si les cases à cocher sont trouvées

    checkboxIndividu.addEventListener('change', function() {
            if (this.checked) {
                checkboxFamille.checked = false;
                checkboxFamille.disabled = true;
            } else {
                checkboxFamille.disabled = false;
            }
        });

    checkboxFamille.addEventListener('change', function() {
            if (this.checked) {
                checkboxIndividu.checked = false;
                checkboxIndividu.disabled = true;
            } else {
                checkboxIndividu.disabled = false;
            }
        });
};
</script>
<br>
"""