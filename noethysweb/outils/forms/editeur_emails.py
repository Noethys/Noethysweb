# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, HTML
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.models import Mail, AdresseMail
from django_summernote.widgets import SummernoteInplaceWidget
from outils.widgets import Pieces_jointes


class Formulaire(FormulaireBase, ModelForm):
    action = forms.CharField(label="Action", required=False)
    objet = forms.CharField(label="Objet", required=False)
    html = forms.CharField(label="Texte", widget=SummernoteInplaceWidget(attrs={'summernote': {'width': '100%', 'height': '400px'}}), required=False)
    pieces_jointes = forms.CharField(label="Pièces jointes", required=False, widget=Pieces_jointes())
    # selection = forms.ChoiceField(label="Sélection", widget=forms.RadioSelect, choices=[("TOUS", "Tous les destinataires"), ("SELECTION", "Les destinataires qui n'ont pas déjà reçu le message")], initial="SELECTION", required=False)

    class Meta:
        model = Mail
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        idmail = kwargs.pop("idmail", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_editeur_emails'
        self.helper.form_method = 'post'
        self.helper.attrs = {'enctype': 'multipart/form-data'}

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Sélectionne l'adresse d'expédition
        self.fields["adresse_exp"].queryset = AdresseMail.objects.filter(pk__in=self.request.user.Get_adresses_exp_possibles(), actif=True).order_by("adresse")
        if not self.fields["adresse_exp"].queryset.count():
            self.fields['adresse_exp'].help_text = """<span class='text-danger'><i class='fa fa-warning text-danger'></i> Vous devez vérifier qu'une adresse d'expédition a été créée dans le menu 
                                                    Paramétrage > Adresses d'expédition et que vous l'avez rattachée à la structure (Menu Paramétrage > Structures). Vous pouvez
                                                    également associer une adresse d'expédition à votre compte utilisateur dans la partie Administrateur.</span>"""
        if not idmail:
            self.fields['adresse_exp'].initial = self.request.user.Get_adresse_exp_defaut()

        self.fields['selection'].required = False

        # Affichage
        self.helper.layout = Layout(
            Commandes(enregistrer=False, ajouter=False, annuler=False, aide=False, autres_commandes=[
                    HTML("""<a class="btn btn-primary" id="bouton_envoyer" title="Envoyer"><i class="fa fa-send-o margin-r-5"></i>Envoyer</a> """),
                    HTML("""<a class="btn btn-danger" title="Fermer" href='{% url 'outils_toc' %}'><i class="fa fa-ban margin-r-5"></i>Fermer</a> """),
                    HTML("""<button type="submit" name="enregistrer_brouillon" title="Enregistrer le brouillon" class="btn btn-default"><i class="fa fa-save margin-r-5"></i>Enregistrer le brouillon</button> """),
                    HTML(EXTRA_HTML),
                ],
            ),
            Hidden('action', value=''),
            Field('objet'),
            Field('adresse_exp'),
            # Field('document'),
            Field('html'),
            Field("selection"),
            Field('pieces_jointes'),
        )



EXTRA_HTML = """
    
<div class="btn-group">
    <a type='button' class='btn btn-default' style='margin-top: 2px;' dropdown-toggle' title="Charger un modèle" data-toggle="dropdown" href='#'><i class="fa fa-file-text-o margin-r-5"></i>Charger un modèle</a>
    <ul class="dropdown-menu">
        {% for modele in modeles %}
            <li class="dropdown-item"><a tabindex="-1" href="#" class="modele_email" data-idmodele="{{ modele.pk }}">{{ modele.nom }}{% if modele.defaut %} (Modèle par défaut){% endif %}</a></li>
        {% empty %}
            <li class="dropdown-header">Aucun modèle disponible</li>
        {% endfor %}
    </ul>
</div>

<div class="btn-group">
    <a type='button' class='btn btn-default' style='margin-top: 2px;' dropdown-toggle' title="Insérer une signature" data-toggle="dropdown" href='#'><i class="fa fa-file-text-o margin-r-5"></i>Insérer une signature</a>
    <ul class="dropdown-menu">
        {% for signature in signatures %}
            <li class="dropdown-item"><a tabindex="-1" href="#" class="signature_email" data-idsignature="{{ signature.pk }}">{{ signature.nom }}</a></li>
        {% empty %}
            <li class="dropdown-header">Aucune signature disponible</li>
        {% endfor %}
    </ul>
</div>

<script>
    $(document).ready(function() {
        // Charger un modèle d'emails
        $(".modele_email").on('click', function(event) {
            event.preventDefault();
            $.ajax({
                type: "POST",
                url: "{% url 'ajax_get_modele_email' %}",
                data: {
                    idmodele: this.dataset.idmodele,
                    csrfmiddlewaretoken: "{{ csrf_token }}",
                },
                datatype: "json",
                success: function(data){
                    $('#id_html').summernote('code', data.html);
                    $('#id_objet').val(data.objet);
                },
            });
        });
        
        // Insérer une signature
        $(".signature_email").on('click', function(event) {
            event.preventDefault();
            $.ajax({
                type: "POST",
                url: "{% url 'ajax_get_signature_email' %}",
                data: {
                    idsignature: this.dataset.idsignature,
                    csrfmiddlewaretoken: "{{ csrf_token }}",
                },
                datatype: "json",
                success: function(data){
                    var node = $("<span></span>").html(data.html)[0];
                    $('#id_html').summernote("editor.insertNode", node);
                },
            });
        });

    });
</script>
"""
