# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.


import datetime
from django import forms
from django.forms import ModelForm
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, HTML, Fieldset, Div
from crispy_forms.bootstrap import Field, PrependedText
from core.forms.select2 import Select2MultipleWidget, Select2Widget
from core.forms.base import FormulaireBase
from core.models import Famille, Cotisation, Activite, Rattachement, TypeCotisation, UniteCotisation
from core.widgets import DatePickerWidget
from core.utils.utils_commandes import Commandes
from core.utils import utils_preferences, utils_texte
from cotisations.widgets import Selection_beneficiaires_cotisation
from fiche_famille.widgets import Prestation_cotisation


class Formulaire(FormulaireBase, ModelForm):
    # Carte
    carte = forms.BooleanField(label="Créer", initial=False, required=False)

    # Facturation
    facturer = forms.BooleanField(label="Facturer", initial=False, required=False)
    date_facturation = forms.DateField(label="Date", required=False, widget=DatePickerWidget())
    label_prestation = forms.CharField(label="Label", required=False)
    montant = forms.DecimalField(label="Montant", max_digits=6, decimal_places=2, initial=0.0, required=False)

    # Activités
    activites = forms.ModelMultipleChoiceField(label="Activités", widget=Select2MultipleWidget(), queryset=Activite.objects.all(), required=False)

    # Bénéficiaires pour la saisie par lot
    beneficiaires_familles = forms.CharField(label="Familles", required=False, widget=Selection_beneficiaires_cotisation(attrs={"categorie": "familles"}))
    beneficiaires_individus = forms.CharField(label="Individus", required=False, widget=Selection_beneficiaires_cotisation(attrs={"categorie": "individus"}))

    class Meta:
        model = Cotisation
        fields = "__all__"
        widgets = {
            'observations': forms.Textarea(attrs={'rows': 3}),
            'date_debut': DatePickerWidget(),
            'date_fin': DatePickerWidget(),
            'date_creation_carte': DatePickerWidget(),
            "prestation": Prestation_cotisation(),
        }
        labels = {
            "type_cotisation": "Type",
            "unite_cotisation": "Unité",
        }

    def __init__(self, *args, **kwargs):
        idfamille = kwargs.pop("idfamille", None)
        idindividu = kwargs.pop("idindividu", None)
        idtype_cotisation = kwargs.pop("idtype_cotisation", None)
        idunite_cotisation = kwargs.pop("idunite_cotisation", None)
        super(Formulaire, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_id = 'famille_cotisations_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Définit la famille associée
        if idfamille:
            famille = Famille.objects.get(pk=idfamille)

        # Liste les types de cotisation
        condition_structure = Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)
        self.fields['type_cotisation'].queryset = TypeCotisation.objects.filter(condition_structure)

        # Type et unité par défaut
        if not self.instance.idcotisation:
            type_cotisation = TypeCotisation.objects.filter(defaut=True).first()
            if type_cotisation:
                self.fields["type_cotisation"].initial = type_cotisation
                unite_cotisation = UniteCotisation.objects.filter(type_cotisation=type_cotisation, defaut=True).first()
                if unite_cotisation:
                    self.fields["unite_cotisation"].initial = unite_cotisation

        if idtype_cotisation:
            self.fields["type_cotisation"].initial = idtype_cotisation
        if idunite_cotisation:
            self.fields["unite_cotisation"].initial = idunite_cotisation

        # Individu
        if idfamille:
            rattachements = Rattachement.objects.select_related('individu').filter(famille=famille).order_by("individu__nom", "individu__prenom")
            self.fields["individu"].choices = [(None, "---------")] + [(rattachement.individu.idindividu, rattachement.individu) for rattachement in rattachements]

        if idindividu:
            self.fields["individu"].initial = idindividu

        # Dates
        self.fields["date_creation_carte"].initial = datetime.date.today()
        self.fields["date_facturation"].initial = datetime.date.today()

        # Numéro
        derniere_cotisation = Cotisation.objects.last()
        numero = derniere_cotisation.numero if derniere_cotisation and derniere_cotisation.numero else 0
        self.fields["numero"].initial = utils_texte.Incrementer(str(numero))

        # Importation
        individu_type = ""
        if self.instance.idcotisation != None:
            # Individu
            individu_type = self.instance.type_cotisation.type

            # Unité
            liste_unites = UniteCotisation.objects.filter(type_cotisation=self.instance.type_cotisation).order_by('date_debut')
            self.fields["unite_cotisation"].choices = [(unite.pk, unite.nom) for unite in liste_unites]

            # Carte
            if self.instance.date_creation_carte != None:
                self.fields["carte"].initial = True
            else:
                self.fields["carte"].initial = False

            # Prestation
            if self.instance.prestation:
                self.fields["facturer"].initial = True
                self.fields["date_facturation"].initial = self.instance.prestation.date
                self.fields["label_prestation"].initial = self.instance.prestation.label
                self.fields["montant"].initial = self.instance.prestation.montant
            else:
                self.fields["facturer"].initial = False

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden('famille', value=idfamille),
            Hidden('individu_type', value=individu_type),
            Hidden('idunite_cotisation_forcee', value=idunite_cotisation),
            Fieldset("Adhésion",
                Field('type_cotisation'),
                Field('unite_cotisation'),
                Field('individu'),
                Field('date_debut'),
                Field('date_fin'),
            ),
            Fieldset("Carte d'adhérent",
                Field('carte'),
                Div(
                    Field('date_creation_carte'),
                    Field("numero"),
                    # Field('depot_cotisation'),
                    id="div_carte"
                ),
            ),
            Fieldset("Facturation",
                Field('facturer'),
                Div(
                    Field('date_facturation'),
                    Field('label_prestation'),
                    PrependedText('montant', utils_preferences.Get_symbole_monnaie()),
                    Field('prestation', type="hidden" if not idfamille else None),
                    id="div_facturer"
                ),
            ),
            Fieldset("Options",
                Field('activites'),
                Field('observations'),
            ),
            HTML(EXTRA_SCRIPT),
        )

        # Si c'est pour une saisie par lot
        if not idfamille:
            self.fields["type_cotisation"].disabled = True
            self.fields["unite_cotisation"].disabled = True
            self.helper.layout.pop(0)
            self.helper.layout.append(Fieldset("Bénéficiaires"))

    def clean(self):
        # Individu
        if self.cleaned_data["type_cotisation"].type == "individu":
            if not self.cleaned_data["individu"]:
                self.add_error("individu", "Vous devez sélectionner un individu bénéficiaire")
                return
        else:
            self.cleaned_data["individu"] = None

        # Carte
        if self.cleaned_data["carte"] == True:
            if not self.cleaned_data["date_creation_carte"]:
                self.add_error("date_creation_carte", "Vous devez saisir une date de création de la carte d'adhésion")
                return
            if not self.cleaned_data["numero"]:
                self.add_error("numero", "Vous devez saisir une numéro d'adhésion")
                return
        else:
            self.cleaned_data["date_creation_carte"] = None
            self.cleaned_data["numero"] = None

        # Facturer
        if self.cleaned_data["facturer"] == True:
            if not self.cleaned_data["date_facturation"]:
                self.add_error("date_facturation", "Vous devez saisir une date de facturation")
                return
            if not self.cleaned_data["label_prestation"]:
                self.add_error("label_prestation", "Vous devez saisir un label pour la prestation à générer")
                return
            # if not self.cleaned_data["montant"]:
            #     self.add_error("montant", "Vous devez saisir un montant pour la prestation à générer")
            #     return
        else:
            self.cleaned_data["date_facturation"] = None
            self.cleaned_data["label_prestation"] = None
            self.cleaned_data["montant"] = None

        return self.cleaned_data


EXTRA_SCRIPT = """
{% load static %}
<script type="text/javascript" src="{% static 'lib/bootbox/bootbox.min.js' %}"></script>

<script>

var individu_type = $("input:hidden[name='individu_type']").val();
var famille = $("input:hidden[name='famille']").val();
var idunite_cotisation_forcee = $("input:hidden[name='idunite_cotisation_forcee']").val();

$(document).ready(function() {
    $("#bouton_generer_cotisations").on('click', function(event) {
        event.preventDefault();
        bootbox.dialog({
            title: "Confirmation",
            message: "Confirmez-vous la génération des adhésions ?",
            buttons: {
                ok: {
                    label: "<i class='fa fa-check'></i> Valider",
                    className: 'btn-primary',
                    callback: function(){
                        toastr.info("La génération des adhésions est en cours. Merci de patienter...");
                        $('#bouton_generer_cotisations').html("<i class='fa fa-refresh fa-spin margin-r-5'></i> Générer les adhésions");
                        $('#famille_cotisations_form').submit();
                    }
                },
                cancel: {
                    label: "<i class='fa fa-ban'></i> Annuler",
                    className: 'btn-danger',
                }
            }
        });
    });
});
        

// Actualise la liste des unités en fonction du type sélectionné
function On_change_type() {
    var idtype_cotisation = $("#id_type_cotisation").val();
    var idunite_cotisation = $("#id_unite_cotisation").val();
    if (idunite_cotisation_forcee === "None") {
        $.ajax({ 
            type: "POST",
            url: "{% url 'ajax_on_change_type_cotisation' %}",
            data: {'idtype_cotisation': idtype_cotisation},
            success: function (data) { 
                $("#id_unite_cotisation").html(data); 
                On_change_unite();
            }
        });
    }
};
$(document).ready(function() {
    $('#id_type_cotisation').change(On_change_type);
    if (individu_type == '') {
        On_change_type.call($('#id_type_cotisation').get(0));
    };
});

function On_change_unite() {
    $.ajax({ 
        type: "POST",
        url: "{% url 'ajax_on_change_unite_cotisation' %}",
        data: {
            'idunite_cotisation': $("#id_unite_cotisation").val(),
            'idfamille': famille
        },
        success: function (data) { 
            // Période de validité
            $('#id_date_debut').datepicker("setDate", data.date_debut);
            $('#id_date_fin').datepicker("setDate", data.date_fin);
            // Individu
            if ((data.type == 'individu') && (famille !== 'None')) {
                $('#div_id_individu').show();
            } else {
                $('#div_id_individu').hide();
            };
            // Si mode saisie par lot
            if (famille == 'None') {
                $('#div_id_beneficiaires_individus').hide();
                $('#div_id_beneficiaires_familles').hide();
                if ($("#id_unite_cotisation").val() !== '') {
                    if (data.type == 'individu') {
                        $('#div_id_beneficiaires_individus').show();
                    } else {
                        $('#div_id_beneficiaires_familles').show();
                    }
                }
            }
            // Carte
            if (data.carte == true) {
                $('#id_carte').prop("checked", true);
                $('#id_date_creation_carte').val(data.date_creation_carte);
                $('#id_numero').val(data.numero);
            } else {
                $('#id_carte').prop("checked", false);
            }
            // Facturer
            if ((data.montant == '0.00') || (data.montant == undefined) || (data.montant == null)){
                $('#id_facturer').prop("checked", false);
            } else {
                $('#id_facturer').prop("checked", true);
                $('#id_label_prestation').val(data.label_prestation);
                $('#id_montant').val(data.montant);
            }
            // Affichage
            On_change_carte();
            On_change_facturer();
        }
    });
};
$(document).ready(function() {
    $('#id_unite_cotisation').change(On_change_unite);
    if (individu_type == '') {
        On_change_unite.call($('#id_unite_cotisation').get(0));
    };
});


// Si importation d'une cotisation
$(document).ready(function() {
    $.ajax({ 
        type: "POST",
        url: "{% url 'ajax_on_change_unite_cotisation' %}",
        data: {
            'idunite_cotisation': $("#id_unite_cotisation").val(),
            'idfamille': famille
        },
        success: function (data) { 
            // Individu
            if (data.type == 'individu') {
                $('#div_id_individu').show();
            } else {
                $('#div_id_individu').hide();
            };
            // Carte
            if ($('#id_carte').prop("checked") == false) {
                $('#id_date_creation_carte').val(data.date_creation_carte);
                $('#id_numero').val(data.numero);
            };
            // Facturer
            if ($('#id_facturer').prop("checked") == false) {
                $('#id_label_prestation').val(data.label_prestation);
                $('#id_montant').val(data.montant);
            };
        }
    });
});


// Carte
function On_change_carte() {
    $('#div_carte').hide();
    if ($('#id_carte').prop("checked")) {
        $('#div_carte').show();
    };
}
$(document).ready(function() {
    $('#id_carte').on('change', On_change_carte);
    On_change_carte.call($('#id_carte').get(0));
});


// Facturer
function On_change_facturer() {
    $('#div_facturer').hide();
    if ($('#id_facturer').prop("checked")) {
        $('#div_facturer').show();
    };
}
$(document).ready(function() {
    $('#id_facturer').on('change', On_change_facturer);
    On_change_facturer.call($('#id_facturer').get(0));
});


</script>
"""

class Formulaire_type_cotisation(FormulaireBase, forms.Form):
    type_cotisation = forms.ModelChoiceField(label="Type d'adhésion", widget=Select2Widget(), queryset=TypeCotisation.objects.none().order_by("nom"), required=True)
    unite_cotisation = forms.ModelChoiceField(label="Unité d'adhésion", widget=Select2Widget(), queryset=UniteCotisation.objects.none().order_by("nom"), required=True)
    affichage_beneficiaires = forms.ChoiceField(label="Liste de bénéficiaires", initial=0, required=True, choices=[
        (0, "Afficher tous les bénéficiaires potentiels"),
        (1, "Afficher uniquement les bénéficiaires potentiels qui n'ont jamais adhéré à cette unité d'adhésion"),
    ])

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop("instance", None)
        super(Formulaire_type_cotisation, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'

        # Sélectionne uniquement les activités autorisées
        condition_structure = Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)
        self.fields["type_cotisation"].queryset = TypeCotisation.objects.filter(condition_structure).order_by("nom")

        self.helper.layout = Layout(
            Commandes(enregistrer_label="<i class='fa fa-check margin-r-5'></i>Valider", ajouter=False, annuler_url="{{ view.get_success_url }}"),
            Fieldset("Sélection de l'adhésion à créer",
                Field("type_cotisation"),
                Field("unite_cotisation"),
            ),
            Fieldset("Options",
                Field("affichage_beneficiaires"),
            ),
            HTML(EXTRA_SCRIPT_2),
        )


EXTRA_SCRIPT_2 = """
<script>

// Actualise la liste des unités en fonction du type sélectionné
function On_change_type() {
    var idtype_cotisation = $("#id_type_cotisation").val();
    var idunite_cotisation = $("#id_unite_cotisation").val();
    $('#div_id_unite_cotisation').hide();
    if ($("#id_type_cotisation").val()) {
        $('#div_id_unite_cotisation').show();
    };
    $.ajax({ 
        type: "POST",
        url: "{% url 'ajax_on_change_type_cotisation' %}",
        data: {
            idtype_cotisation: idtype_cotisation, 
            csrfmiddlewaretoken: '{{ csrf_token }}'
        },
        success: function (data) { 
            $("#id_unite_cotisation").html(data); 
            On_change_unite();
        }
    });
};
$(document).ready(function() {
    $('#id_type_cotisation').change(On_change_type);
    On_change_type.call($('#id_type_cotisation').get(0));
});

</script>
"""
