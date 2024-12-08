# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm, HiddenInput
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, HTML
from crispy_forms.bootstrap import Field
from django_summernote.widgets import SummernoteInplaceWidget
from django_select2.forms import Select2TagWidget
from core.forms.base import FormulaireBase
from core.models import Mail, AdresseMail, Rattachement
from core.utils.utils_commandes import Commandes
from outils.widgets import Documents_joints
from outils.forms.editeur_emails import EXTRA_HTML


class Formulaire(FormulaireBase, ModelForm):
    objet = forms.CharField(label="Objet", required=False)
    html = forms.CharField(label="Texte", widget=SummernoteInplaceWidget(attrs={'summernote': {'width': '100%', 'height': '400px'}}), required=False)
    documents = forms.CharField(label="Documents", required=False, widget=Documents_joints())
    dest = forms.MultipleChoiceField(label="Destinataires", required=False, widget=Select2TagWidget(attrs={"lang": "fr", "data-width": "100%", "data-minimum-input-length": 0, "title": "Sélectionnez une adresse dans la liste ou tapez-la directement"}), choices=[])

    class Meta:
        model = Mail
        fields = ["objet", "html", "adresse_exp"]

    def __init__(self, *args, **kwargs):
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
        if not self.instance:
            self.fields['adresse_exp'].initial = self.request.user.Get_adresse_exp_defaut()

        # Sélection des destinataires
        if self.instance:
            destinataire = self.instance.destinataires.first()
            liste_dest = []
            selection_defaut = None

            if destinataire.famille:
                for rattachement in Rattachement.objects.select_related("individu").filter(famille=destinataire.famille):
                    for mail in (rattachement.individu.mail, rattachement.individu.travail_mail):
                        if mail:
                            dest = "%s <%s>" % (rattachement.individu.Get_nom(), mail)
                            if mail == destinataire.adresse:
                                selection_defaut = dest
                            liste_dest.append(dest)

            if destinataire.collaborateur:
                for mail in (destinataire.collaborateur.mail, destinataire.collaborateur.travail_mail):
                    if mail:
                        dest = "%s <%s>" % (destinataire.collaborateur.Get_nom(), mail)
                        liste_dest.append(dest)
                        if not selection_defaut:
                            selection_defaut = dest

            if destinataire.categorie == "saisie_libre" and destinataire.adresse:
                dest = "%s <%s>" % (destinataire.adresse, destinataire.adresse)
                liste_dest.append(dest)
                selection_defaut = dest

            self.fields['dest'].choices = [(dest, dest) for dest in liste_dest]
            if selection_defaut:
                self.fields['dest'].initial = selection_defaut

            if destinataire.documents.all():
                self.fields['documents'].widget.attrs['documents'] = destinataire.documents
            else:
                self.fields['documents'].widget = HiddenInput()

        # Affichage
        self.helper.layout = Layout(
            Hidden("idmail", value=self.instance.pk),
            Commandes(enregistrer=False, ajouter=False, annuler=False, aide=False,
                      autres_commandes=[
                          HTML("""<a class="btn btn-primary" id="bouton_envoyer" title="Envoyer"><i class="fa fa-send-o margin-r-5"></i>Envoyer</a> """),
                          HTML("""<a class="btn btn-danger" title="Fermer" onclick="$('#modal_editeur_emails').modal('hide');"><i class="fa fa-ban margin-r-5"></i>Fermer</a> """),
                          HTML("""<button type="submit" name="enregistrer_brouillon" title="Enregistrer le brouillon" class="btn btn-default"><i class="fa fa-save margin-r-5"></i>Enregistrer le brouillon</button> """),
                          HTML(EXTRA_HTML),
                      ],
            ),
            Field('objet'),
            Field('adresse_exp'),
            Field('dest'),
            Field('documents'),
            Field('html'),
        )
