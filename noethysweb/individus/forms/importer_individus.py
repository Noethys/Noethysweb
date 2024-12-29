# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.core.validators import FileExtensionValidator
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase


class Formulaire_parametres(FormulaireBase, forms.Form):
    fichier = forms.FileField(label="Fichier Excel (xlsx)", widget=forms.FileInput(attrs={'accept':'text/xlsx'}), required=True, validators=[FileExtensionValidator(allowed_extensions=["xlsx"])])
    type_import = forms.ChoiceField(label="Constitution du fichier", choices=[("FAMILLES", "Une ligne par famille"), ("INDIVIDUS", "Une ligne par individu")], initial="FAMILLES", required=False)
    ligne_entete = forms.BooleanField(label="La première ligne contient les entêtes des colonnes", required=False, initial=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire_parametres, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'
        self.helper.attrs = {'enctype': 'multipart/form-data'}
        self.helper.use_custom_control = False

        # Affichage
        self.helper.layout = Layout(
            Field("fichier"),
            Field("type_import"),
            Field("ligne_entete"),
        )


LISTE_DONNEES_INDIVIDU = [
    {"code": "CIVILITE", "titre": "Civilité", "description": "Monsieur = M, Monsieur, Mr, M., H, Homme, Père. Melle = Melle, Mademoiselle, Mère. Madame = Mme, Madame, Femme, Mère. Enfant = Garçon, Fille. Autres = Collectivité, Association, Organisme, Entreprise."},
    {"code": "NOM", "titre": "Nom de famille", "description": "Exemples : DURAND, DUPOND..."},
    {"code": "NOMJFILLE", "titre": "Nom de naissance", "description": "Exemples : DURAND, DUPOND..."},
    {"code": "PRENOM", "titre": "Prénom", "description": "Exemples : Kévin, Sophie..."},
    {"code": "DATE_NAISS", "titre": "Date de naissance", "description": "Format : JJ/MM/AAAA. Exemple : 01/02/2003."},
    {"code": "CP_NAISS", "titre": "Code postal de la ville de naissance", "description": "Format : XXXXX. Exemple : 29200."},
    {"code": "VILLE_NAISS", "titre": "Nom de la ville de naissance", "description": "Exemples : BREST, TOULOUSE..."},
    {"code": "RUE_RESID", "titre": "Rue de résidence", "description": "Exemple : 10 rue des oiseaux."},
    {"code": "CP_RESID", "titre": "Code postal de résidence", "description": "Exemple : 29200."},
    {"code": "VILLE_RESID", "titre": "Nom de la ville de résidence", "description": "Exemples : BREST, TOULOUSE..."},
    {"code": "SECTEUR_RESID", "titre": "Secteur de résidence", "description": "Cette valeur doit obligatoirement exister dans les secteurs déjà paramétrés (Menu Paramétrage > Secteurs). Exemples : Brest Nord."},
    {"code": "TELEPHONE_DOMICILE", "titre": "Téléphone du domicile", "description": "Format : XX.XX.XX.XX.XX ou XXXXXXXXXX ou XX-XX-XX-XX-XX. Exemple : 01.02.03.04.05."},
    {"code": "TELEPHONE_PORTABLE", "titre": "Téléphone portable", "description": "Format : XX.XX.XX.XX.XX ou XXXXXXXXXX ou XX-XX-XX-XX-XX. Exemple : 01.02.03.04.05."},
    {"code": "TELEPHONE_PRO", "titre": "Téléphone professionnel", "description": "Format : XX.XX.XX.XX.XX ou XXXXXXXXXX ou XX-XX-XX-XX-XX. Exemple : 01.02.03.04.05."},
    {"code": "EMAIL_PERSONNEL", "titre": "Email personnel", "description": "Format : xxxxxxx@xxxxx.xx. Exemple : monadresse@test.com"},
    {"code": "EMAIL_PRO", "titre": "Email professionnel", "description": "Format : xxxxxxx@xxxxx.xx. Exemple : monadresse@test.com"},
    {"code": "PROFESSION", "titre": "Profession", "description": "Exemple : Charpentier, secrétaire..."},
    {"code": "EMPLOYEUR", "titre": "Employeur", "description": "Exemple : SNCF, France Telecom..."},
    {"code": "MEMO", "titre": "Mémo", "description": "Texte libre."},
]


def Get_champs_famille():
    liste_champs = []
    for index in range(1, 7):
        for item in LISTE_DONNEES_INDIVIDU:
            liste_champs.append({"code": "%s_INDIVIDU%d" % (item["code"], index), "titre": "Individu %d - %s" % (index, item["titre"]), "description": item["description"]})
    return liste_champs


DICT_TYPE_DONNEE = {
    "FAMILLES" : [
        {"code": "", "titre": "Non affecté", "description": ""},
    ] + Get_champs_famille(),
    "INDIVIDUS": [
        {"code": "", "titre": "Non affecté", "description": ""},
        {"code": "IDFAMILLE", "titre": "ID Famille", "description": "l'ID Famille est une chaîne numérique ou alphanumérique qui permet de lier les individus à une famille. Exemple : 320, AXB, GHJ246... Attention, si vous ne renseignez pas de ID Famille, seules des fiches individuelles non rattachées seront créées. Ce sera à vous de les rattacher manuellement par la suite."},
    ] + LISTE_DONNEES_INDIVIDU,
}


class Formulaire_colonne(FormulaireBase, forms.Form):
    type_donnee = forms.ChoiceField(label="Type de donnée", choices=[], initial="", required=False)

    def __init__(self, *args, **kwargs):
        type_import = kwargs.pop("type_import", "FAMILLES")
        super(Formulaire_colonne, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_colonne'
        self.helper.form_method = 'post'
        self.helper.use_custom_control = False

        self.fields["type_donnee"].choices = [(item["code"], item["titre"]) for item in DICT_TYPE_DONNEE[type_import]]

        # Affichage
        self.helper.layout = Layout(
            Field("type_donnee"),
        )
