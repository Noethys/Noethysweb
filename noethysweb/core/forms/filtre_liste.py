# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, datetime
import dateutil.parser
from operator import itemgetter
from django import forms
from django.http import JsonResponse
from django.template import Template, RequestContext
from django.shortcuts import redirect
from django.utils.html import escapejs
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, HTML, Div, ButtonHolder
from crispy_forms.bootstrap import Field
from core.forms.select2 import Select2MultipleWidget
from core.forms.base import FormulaireBase
from core.utils import utils_dates
from core.models import FiltreListe
from core.widgets import DatePickerWidget, SelectionActivitesWidget, DateTimePickerWidget
from consommations.widgets import SelectionEcolesWidget, SelectionClassesWidget, SelectionNiveauxWidget, SelectionEvenementsWidget


def Get_form_filtres(request):
    """ Renvoie le form par ajax """
    idfiltre = request.POST.get("idfiltre")
    nom_view = request.POST.get("view")
    nom_liste = nom_view[4:nom_view.find(" object at ")]

    # Si liste classique
    nom_view = nom_liste.replace(".Liste", "")
    nom_classe = "Liste"

    # Si liste de type Consulter
    if ".Consulter" in nom_liste:
        nom_view = nom_liste.replace(".Consulter", "")
        nom_classe = "Consulter"

    # Importation de la view
    import importlib
    view = importlib.import_module(nom_view)
    liste_view = getattr(view, nom_classe)
    model = getattr(liste_view, "model", None)

    # Récupération des filtres
    filtres = colonnes = []
    if hasattr(liste_view, "datatable_class"):
        filtres = getattr(liste_view.datatable_class, "filtres", [])

    if hasattr(liste_view, "colonnes"):
        colonnes = liste_view.colonnes
        filtres = liste_view.filtres

    # Génération de filtres génériques
    for filtre in filtres:

        if filtre.startswith("igenerique:"):
            nom_champ = filtre.split(":")[1]
            filtres.extend(["%s:%s" % (txt, nom_champ) for txt in ("ipresent", "iscolarise", "datenaiss", "age")])
            filtres.extend(["%s%s" % ("" if nom_champ == "pk" else nom_champ + "__", txt) for txt in ("nom", "prenom", "rue_resid", "cp_resid", "ville_resid", "tel_domicile", "tel_mobile", "mail", "date_creation")])

        if filtre.startswith("fgenerique:"):
            nom_champ = filtre.split(":")[1]
            filtres.extend(["%s:%s" % (txt, nom_champ) for txt in ("fpresent", "fscolarise")])
            filtres.extend(["%s%s" % ("" if nom_champ == "pk" else nom_champ + "__", txt) for txt in ("nom", "rue_resid", "cp_resid", "ville_resid", "date_creation")])

    # Suppression des filtres en doublon
    filtres = list({filtre: True for filtre in filtres}.keys())

    # Création du formulaire
    if filtres or colonnes:
        form = Formulaire(model=model, filtres=filtres, colonnes=colonnes, nom_liste=nom_liste, idfiltre=idfiltre, request=request)
        html = "{% load crispy_forms_tags %} {% crispy form %}"
        data = Template(html).render(RequestContext(request, {"form": form}))
    else:
        data = "Aucun filtre n'est disponible pour cette liste."
    return JsonResponse({"html": data})


def Ajouter_filtre(request):
    """ Validation du filtre à ajouter """
    valeurs = json.loads(request.POST.get("valeurs"))
    dict_resultat = {
        "champ": valeurs["champ"],
        "criteres": [],
    }
    if "options" in valeurs:
        dict_resultat["options"] = valeurs["options"]
    liste_labels_criteres = []
    for key, valeur in valeurs.items():
        if key.startswith("condition"):
            dict_resultat["condition"] = valeur

        if key.startswith("critere"):
            type_critere = key.replace("critere_", "")
            if "datetime" in type_critere:
                dict_resultat["criteres"].append(str(dateutil.parser.parse(valeur, dayfirst=True)))
            elif "date_naiss" in type_critere:
                if valeur:
                    periode_str = utils_dates.ConvertPeriodeFrToDate(valeur)
                    if not periode_str:
                        return JsonResponse({"erreur": "Le critère date de naissance semble être erronée"}, status=401)
                    dict_resultat["criteres"].append(valeur)
                    liste_labels_criteres.append("né(e) entre '%s'" % valeur)
            elif "date" in type_critere:
                dict_resultat["criteres"].append(str(utils_dates.ConvertDateFRtoDate(valeur)))
            else:
                dict_resultat["criteres"].append(valeur)
            if not valeur and key not in ("critere_date_optionnelle", "critere_periode_naiss"):
                return JsonResponse({"erreur": "Vous n'avez pas renseigné correctement le critère"}, status=401)
            if key not in ("critere_etats", "critere_etats_inscriptions", "critere_periode_naiss"):
                liste_labels_criteres.append("'%s'" % valeur)

        if key.startswith("liste_"):
            if not valeur:
                return JsonResponse({"erreur": "Vous devez cocher au moins une ligne dans la liste"}, status=401)
            type_liste = key.replace("liste_", "")
            dict_resultat["criteres"].append(type_liste + ":" + ";".join(valeur))

    traductions_criteres = {
        "EGAL": "est égal à", "DIFFERENT": "est différent de", "CONTIENT": "contient", "NE_CONTIENT_PAS": "ne contient pas",
        "SUPERIEUR": "est supérieur à", "SUPERIEUR_EGAL": "est supérieur ou égal à", "INFERIEUR": "est inférieur à", "INFERIEUR_EGAL": "est inférieur ou égal à",
        "VRAI": "est vrai", "FAUX": "est faux", "COMPRIS": "est compris entre", "INSCRIT": "est inscrit sur une sélection d'activités au ",
        "PRESENT": "a des consommations sur une sélection d'activités entre", "EVENEMENTS": "a des consommations sur une sélection d'évènements",
        "SANS_RESA": "est sans consommation sur une sélection d'activités entre", "EST_VIDE": "est vide", "EST_PAS_VIDE": "n'est pas vide",
        "ECOLES": "est scolarisé sur une sélection d'écoles au", "CLASSES": "est scolarisé sur une sélection de classes",
        "NIVEAUX": "est scolarisé sur une sélection de niveaux scolaires au", "NON_SCOLARISE": "n'est pas scolarisé au",
        "EST_NUL": "est vide", "EST_PAS_NUL": "n'est pas vide",
    }

    if valeurs["champ"].startswith("ipresent") or valeurs["champ"].startswith("iscolarise"): valeurs["label_champ"] = "L'individu"
    if valeurs["champ"].startswith("fpresent") or valeurs["champ"].startswith("fscolarise"): valeurs["label_champ"] = "L'un des membres de la famille"
    if valeurs["champ"].startswith("datenaiss"): valeurs["label_champ"] = "La date de naissance de l'individu"
    if valeurs["champ"].startswith("age"): valeurs["label_champ"] = "L'âge de l'individu"
    if valeurs["champ"].startswith("fprelevement_actif"): valeurs["label_champ"] = "Le prélèvement activé pour la famille"
    if dict_resultat["condition"] in ("INSCRIT", "PRESENT", "SANS_RESA"):
        if "liste_groupes_activites" not in valeurs and "liste_activites" not in valeurs and "liste_groupes" not in valeurs:
            return JsonResponse({"erreur": "Vous devez cocher au moins une ligne dans la liste"}, status=401)
    dict_resultat["label_filtre"] = "%s %s" % (valeurs["label_champ"], traductions_criteres[dict_resultat["condition"].replace("*", "")])
    if liste_labels_criteres:
        dict_resultat["label_filtre"] += " " + " et ".join(liste_labels_criteres)

    # Enregistrement du filtre
    idfiltre = valeurs.get("idfiltre")
    if idfiltre != "None":
        filtre = FiltreListe.objects.get(pk=idfiltre)
        filtre.parametres = json.dumps(dict_resultat)
        filtre.save()
    else:
        nom_liste = valeurs["nom_liste"]
        nom_liste = nom_liste.replace(".Liste", "")
        FiltreListe.objects.create(nom=nom_liste, parametres=json.dumps(dict_resultat), utilisateur=request.user)
    return JsonResponse({"success": True})


def Supprimer_filtre(request, idfiltre=None):
    """ Suppression du filtre de liste """
    FiltreListe.objects.get(pk=idfiltre).delete()
    # Recharge la page
    return redirect(request.META["HTTP_REFERER"])


class Formulaire(FormulaireBase, forms.Form):
    condition1 = forms.ChoiceField(label="Condition", choices=[("EGAL", "Est égal à"), ("DIFFERENT", "Est différent de"), ("CONTIENT", "Contient"), ("NE_CONTIENT_PAS", "Ne contient pas"), ("EST_VIDE", "Est vide"), ("EST_PAS_VIDE", "N'est pas vide")], required=False)
    condition2 = forms.ChoiceField(label="Condition", choices=[("EGAL", "Est égal à"), ("DIFFERENT", "Est différent de"), ("SUPERIEUR", "Est supérieur à"), ("SUPERIEUR_EGAL", "Est supérieur ou égal à"), ("INFERIEUR", "Est inférieur à"), ("INFERIEUR_EGAL", "Est inférieur ou égal à"), ("COMPRIS", "Est compris entre"), ("EST_NUL", "Est vide"), ("EST_PAS_NUL", "N'est pas vide")], required=False)
    condition3 = forms.ChoiceField(label="Condition", choices=[("VRAI", "Est vrai"), ("FAUX", "Est faux")], required=False)
    condition4 = forms.ChoiceField(label="Condition", choices=[("INSCRIT", "Est inscrit sur l'une des activités suivantes"), ("PRESENT", "A des consommations sur l'une des activités suivantes"), ("EVENEMENTS", "A des consommations sur l'un des événements suivants"), ("SANS_RESA", "Est sans consommations sur l'une des activités suivantes")], required=False)
    condition5 = forms.ChoiceField(label="Condition", choices=[("*EGAL", "Est égal à"), ("*DIFFERENT", "Est différent de"), ("*CONTIENT", "Contient"), ("*NE_CONTIENT_PAS", "Ne contient pas"), ("*EST_VIDE", "Est vide"), ("*EST_PAS_VIDE", "N'est pas vide")], required=False)
    condition6 = forms.ChoiceField(label="Condition", choices=[("ECOLES", "Est scolarisé dans l'une des écoles suivantes"), ("CLASSES", "Est scolarisé dans l'une des classes suivantes"), ("NIVEAUX", "Est scolarisé dans l'un des niveaux suivants"), ("NON_SCOLARISE", "N'est pas scolarisé")], required=False)
    critere_texte = forms.CharField(label="Texte", required=False)
    critere_date = forms.DateField(label="Date", widget=DatePickerWidget(attrs={'afficher_fleches': False}), required=False)
    critere_date_optionnelle = forms.DateField(label="Date", widget=DatePickerWidget(attrs={'afficher_fleches': False}), required=False)
    critere_date_min = forms.DateField(label="Date min", widget=DatePickerWidget(attrs={'afficher_fleches': False}), required=False)
    critere_date_max = forms.DateField(label="Date max", widget=DatePickerWidget(attrs={'afficher_fleches': False}), required=False)
    critere_datetime = forms.DateTimeField(label="Date et heure", widget=DateTimePickerWidget(), required=False)
    critere_datetime_min = forms.DateField(label="Date et heure min", widget=DateTimePickerWidget(), required=False)
    critere_datetime_max = forms.DateField(label="Date et heure max", widget=DateTimePickerWidget(), required=False)
    critere_heure = forms.TimeField(label="Heure", widget=DatePickerWidget(attrs={'afficher_fleches': False}), required=False)
    critere_heure_min = forms.TimeField(label="Heure min", widget=DatePickerWidget(attrs={'afficher_fleches': False}), required=False)
    critere_heure_max = forms.TimeField(label="Heure max", widget=DatePickerWidget(attrs={'afficher_fleches': False}), required=False)
    critere_entier = forms.IntegerField(label="Entier", required=False)
    critere_entier_min = forms.IntegerField(label="Entier min", required=False)
    critere_entier_max = forms.IntegerField(label="Entier max", required=False)
    critere_decimal = forms.DecimalField(label="Nombre", required=False)
    critere_decimal_min = forms.DecimalField(label="Nbre min", required=False)
    critere_decimal_max = forms.DecimalField(label="Nbre max", required=False)
    critere_activites = forms.CharField(label="Activités", required=False, widget=SelectionActivitesWidget(attrs={"afficher_groupes": True}))
    critere_ecoles = forms.CharField(label="Ecoles", required=False, widget=SelectionEcolesWidget(attrs={"name": "liste_ecoles"}))
    critere_classes = forms.CharField(label="Classes", required=False, widget=SelectionClassesWidget(attrs={"name": "liste_classes"}))
    critere_niveaux = forms.CharField(label="Niveaux", required=False, widget=SelectionNiveauxWidget(attrs={"name": "liste_niveaux"}))
    critere_evenements = forms.CharField(label="Evénements", required=False, widget=SelectionEvenementsWidget(attrs={"name": "liste_evenements"}), help_text="Vous pouvez uniquement cocher les événements de moins de 1 an.")
    critere_etats = forms.MultipleChoiceField(label="Etats", required=False, widget=Select2MultipleWidget(),
        choices=[("reservation", "Réservation"), ("present", "Présent"), ("attente", "Attente"), ("absentj", "Absence justifiée"), ("absenti", "Absence injustifiée")],
        initial=["reservation", "present"])
    critere_etats_inscriptions = forms.MultipleChoiceField(label="Statuts", required=False, widget=Select2MultipleWidget(),
        choices=[("ok", "Validé"), ("attente", "En attente"), ("refus", "Refusé")], initial=["ok",])
    critere_periode_naiss = forms.CharField(label="Né(e) entre", required=False, widget=forms.TextInput(attrs={"placeholder": "jj/mm/aaaa - jj/mm/aaaa"}))

    dict_types = {
        'BinaryField': {'condition': 'condition5', 'criteres': {"*EGAL": ["critere_texte"], "*DIFFERENT": ["critere_texte"], "*CONTIENT": ["critere_texte"], "*NE_CONTIENT_PAS": ["critere_texte"], "*EST_VIDE": [], "*EST_PAS_VIDE": []}},
        'CharField': {'condition': 'condition1', 'criteres': {"EGAL": ["critere_texte"], "DIFFERENT": ["critere_texte"], "CONTIENT": ["critere_texte"], "NE_CONTIENT_PAS": ["critere_texte"], "EST_VIDE": [], "EST_PAS_VIDE": []}},
        'TextField': {'condition': 'condition1', 'criteres': {"EGAL": ["critere_texte"], "DIFFERENT": ["critere_texte"], "CONTIENT": ["critere_texte"], "NE_CONTIENT_PAS": ["critere_texte"], "EST_VIDE": [], "EST_PAS_VIDE": []}},
        'BooleanField': {'condition': 'condition3', 'criteres': {"VRAI": [], "FAUX": []}},
        'DateField': {'condition': 'condition2', 'criteres': {"EGAL": ["critere_date"], "DIFFERENT": ["critere_date"], "SUPERIEUR": ["critere_date"], "SUPERIEUR_EGAL": ["critere_date"], "INFERIEUR": ["critere_date"], "INFERIEUR_EGAL": ["critere_date"], "COMPRIS": ["critere_date_min", "critere_date_max"], "EST_NUL": [], "EST_PAS_NUL": []}},
        'DateTimeField': {'condition': 'condition2', 'criteres': {"EGAL": ["critere_datetime"], "DIFFERENT": ["critere_datetime"], "SUPERIEUR": ["critere_datetime"], "SUPERIEUR_EGAL": ["critere_datetime"], "INFERIEUR": ["critere_datetime"], "INFERIEUR_EGAL": ["critere_datetime"], "COMPRIS": ["critere_datetime_min", "critere_datetime_max"], "EST_NUL": [], "EST_PAS_NUL": []}},
        'TimeField': {'condition': 'condition2', 'criteres': {"EGAL": ["critere_heure"], "DIFFERENT": ["critere_heure"], "SUPERIEUR": ["critere_heure"], "SUPERIEUR_EGAL": ["critere_heure"], "INFERIEUR": ["critere_heure"], "INFERIEUR_EGAL": ["critere_heure"], "COMPRIS": ["critere_heure_min", "critere_heure_max"], "EST_NUL": [], "EST_PAS_NUL": []}},
        'AutoField': {'condition': 'condition2', 'criteres': {"EGAL": ["critere_entier"], "DIFFERENT": ["critere_entier"], "SUPERIEUR": ["critere_entier"], "SUPERIEUR_EGAL": ["critere_entier"], "INFERIEUR": ["critere_entier"], "INFERIEUR_EGAL": ["critere_entier"], "COMPRIS": ["critere_entier_min", "critere_entier_max"], "EST_NUL": [], "EST_PAS_NUL": []}},
        'IntegerField': {'condition': 'condition2', 'criteres': {"EGAL": ["critere_entier"], "DIFFERENT": ["critere_entier"], "SUPERIEUR": ["critere_entier"], "SUPERIEUR_EGAL": ["critere_entier"], "INFERIEUR": ["critere_entier"], "INFERIEUR_EGAL": ["critere_entier"], "COMPRIS": ["critere_entier_min", "critere_entier_max"], "EST_NUL": [], "EST_PAS_NUL": []}},
        'DecimalField': {'condition': 'condition2', 'criteres': {"EGAL": ["critere_decimal"], "DIFFERENT": ["critere_decimal"], "SUPERIEUR": ["critere_decimal"], "SUPERIEUR_EGAL": ["critere_decimal"], "INFERIEUR": ["critere_decimal"], "INFERIEUR_EGAL": ["critere_decimal"], "COMPRIS": ["critere_decimal_min", "critere_decimal_max"], "EST_NUL": [], "EST_PAS_NUL": []}},
        'ipresent': {'condition': 'condition4', 'criteres': {"INSCRIT": ["critere_activites", "critere_date_optionnelle", "critere_etats_inscriptions", "critere_periode_naiss"], "PRESENT": ["critere_activites", "critere_date_min", "critere_date_max", "critere_etats", "critere_periode_naiss"], "EVENEMENTS": ["critere_evenements", "critere_etats", "critere_periode_naiss"], "SANS_RESA": ["critere_activites", "critere_date_min", "critere_date_max"]}},
        'fpresent': {'condition': 'condition4', 'criteres': {"INSCRIT": ["critere_activites", "critere_date_optionnelle", "critere_etats_inscriptions", "critere_periode_naiss"], "PRESENT": ["critere_activites", "critere_date_min", "critere_date_max", "critere_etats", "critere_periode_naiss"], "EVENEMENTS": ["critere_evenements", "critere_etats", "critere_periode_naiss"], "SANS_RESA": ["critere_activites", "critere_date_min", "critere_date_max"]}},
        'iscolarise': {'condition': 'condition6', 'criteres': {"ECOLES": ["critere_date", "critere_ecoles"], "CLASSES": ["critere_classes"], "NIVEAUX": ["critere_date", "critere_niveaux"], "NON_SCOLARISE": ["critere_date"]}},
        'fscolarise': {'condition': 'condition6', 'criteres': {"ECOLES": ["critere_date", "critere_ecoles"], "CLASSES": ["critere_classes"], "NIVEAUX": ["critere_date", "critere_niveaux"], "NON_SCOLARISE": ["critere_date"]}},
        'fprelevement_actif': {'condition': 'condition3', 'criteres': {"VRAI": [], "FAUX": []}},
        'datenaiss': {'condition': 'condition2', 'criteres': {"EGAL": ["critere_date"], "DIFFERENT": ["critere_date"], "SUPERIEUR": ["critere_date"], "SUPERIEUR_EGAL": ["critere_date"], "INFERIEUR": ["critere_date"], "INFERIEUR_EGAL": ["critere_date"], "COMPRIS": ["critere_date_min", "critere_date_max"], "EST_NUL": [], "EST_PAS_NUL": []}},
        'age': {'condition': 'condition2', 'criteres': {"EGAL": ["critere_entier"], "DIFFERENT": ["critere_entier"], "SUPERIEUR": ["critere_entier"], "SUPERIEUR_EGAL": ["critere_entier"], "INFERIEUR": ["critere_entier"], "INFERIEUR_EGAL": ["critere_entier"], "COMPRIS": ["critere_entier_min", "critere_entier_max"], "EST_NUL": [], "EST_PAS_NUL": []}},
    }

    critere = forms.CharField(label="Critère", required=False)

    def __init__(self, *args, **kwargs):
        model = kwargs.pop("model")
        filtres = kwargs.pop("filtres")
        nom_liste = kwargs.pop("nom_liste")
        idfiltre = kwargs.pop("idfiltre")
        colonnes = kwargs.pop("colonnes")

        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'filtres_form'
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Liste uniquement les activités accessibles pour l'utilisateur
        self.fields["critere_activites"].widget.request = self.request
        self.fields["critere_evenements"].widget.request = self.request

        # Affiche uniquement les événéments récents
        self.fields["critere_evenements"].widget.attrs["date_min"] = datetime.date.today() - datetime.timedelta(days=365)

        # Date du jour
        # self.fields["critere_classes"].widget.attrs.update({"dates": [datetime.date.today()]})

        # Choix du champ à filtrer
        choix_champs = []
        dict_champs = {}
        for filtre in filtres:
            if ":" in filtre:
                # Filtre spécial
                nom_filtre, champ = filtre.split(":")
                nom_champ = None
                if nom_filtre == "ipresent": nom_champ = "Individu : Inscrit/présent"
                if nom_filtre == "fpresent": nom_champ = "Famille : Inscrit/présent"
                if nom_filtre == "iscolarise": nom_champ = "Individu : Scolarisé"
                if nom_filtre == "fscolarise": nom_champ = "Famille : Scolarisé"
                if nom_filtre == "fprelevement_actif": nom_champ = "Famille : Prélèvement actif"
                if nom_filtre == "datenaiss": nom_champ = "Individu : Date de naissance"
                if nom_filtre == "age": nom_champ = "Individu : Age"
                # Mémorisation du champ
                if nom_champ:
                    dict_champs[filtre] = {'type': nom_filtre, 'label': nom_champ}
                    choix_champs.append((filtre, nom_champ))

            else:
                if not colonnes:
                    # Filtre standard
                    elements = filtre.split("__")
                    for field in model._meta.get_fields():
                        if field.name == elements[0]:
                            nom_champ = model._meta.verbose_name.capitalize() + " : " + field.verbose_name

                            # Si c'est un ForeignKey
                            if field.related_model and len(elements) > 1:
                                for field_temp in field.related_model._meta.get_fields():
                                    if field_temp.name == elements[1]:
                                        nom_champ = field.related_model._meta.verbose_name.capitalize() + " : " + field_temp.verbose_name
                                        field = field_temp

                            # Mémorisation du champ
                            dict_champs[filtre] = {'type': field.get_internal_type(), 'label': nom_champ}
                            choix_champs.append((filtre, nom_champ))

                if colonnes:
                    for colonne in colonnes:
                        if colonne.code == filtre:
                            if colonne.label_filtre:
                                nom_champ = "%s : %s" % (colonne.label, colonne.label_filtre)
                            else:
                                nom_champ = colonne.label
                            dict_champs[colonne.code] = {'type': colonne.classe, 'label': nom_champ}
                            choix_champs.append((colonne.code, nom_champ))

        choix_champs = sorted(choix_champs, key=itemgetter(1))
        self.fields["champ"] = forms.ChoiceField(label="Filtre", choices=choix_champs, required=False)

        # Si modification d'un filtre existant
        if idfiltre:
            filtre = FiltreListe.objects.get(pk=idfiltre)
            dict_filtre = json.loads(filtre.parametres)
            # Saisit le champ
            self.fields["champ"].initial = dict_filtre["champ"]
            type_champ = dict_champs[dict_filtre["champ"]]["type"]
            # Saisit la condition
            ctrl_condition = self.dict_types[type_champ]["condition"]
            self.fields[ctrl_condition].initial = dict_filtre["condition"]
            # Saisit les critères
            ctrl_criteres = self.dict_types[type_champ]["criteres"][dict_filtre["condition"]]
            for index, nom_ctrl in enumerate(ctrl_criteres):
                # Si datetime
                if index <= len(dict_filtre["criteres"])-1 and "-" in dict_filtre["criteres"][index] and ":" in dict_filtre["criteres"][index]:
                    dict_filtre["criteres"][index] = datetime.datetime.strptime(dict_filtre["criteres"][index], "%Y-%m-%d %H:%M:%S")
                # Importation de la valeur par défaut
                try:
                    self.fields[nom_ctrl].initial = dict_filtre["criteres"][index]
                except:
                    pass

        # Affichage
        self.helper.layout = Layout(
            HTML(EXTRA_HTML % (escapejs(json.dumps(self.dict_types)), escapejs(json.dumps(dict_champs)))),
            Hidden("nom_liste", nom_liste),
            Hidden("idfiltre", idfiltre),
            Field("champ"),
            Field("condition1"),
            Field("condition2"),
            Field("condition3"),
            Field("condition4"),
            Field("condition5"),
            Field("condition6"),
            Field("critere_activites"),
            Field("critere_evenements"),
            Field("critere_texte"),
            Field("critere_date"),
            Field("critere_date_optionnelle"),
            Field("critere_date_min"),
            Field("critere_date_max"),
            Field("critere_datetime"),
            Field("critere_datetime_min"),
            Field("critere_datetime_max"),
            Field("critere_heure"),
            Field("critere_heure_min"),
            Field("critere_heure_max"),
            Field("critere_entier"),
            Field("critere_entier_min"),
            Field("critere_entier_max"),
            Field("critere_decimal"),
            Field("critere_decimal_min"),
            Field("critere_decimal_max"),
            Field("critere_ecoles"),
            Field("critere_classes"),
            Field("critere_niveaux"),
            Field("critere_etats"),
            Field("critere_etats_inscriptions"),
            Field("critere_periode_naiss"),
            ButtonHolder(
                Div(
                    HTML("""<button type="button" class="btn btn-primary" onclick="valider_ajout_filtre()"><i class="fa fa-check margin-r-5"></i>Valider</button>"""),
                    HTML("""<button type="button" class="btn btn-danger" data-dismiss="modal"><i class='fa fa-ban margin-r-5'></i>Annuler</button>"""),
                    css_class="modal-footer", style="padding-bottom:0px;padding-right:0px;"
                ),
            ),
        )


EXTRA_HTML = """
<script>

    var dict_types = JSON.parse("%s");
    var dict_champs = JSON.parse("%s");

    function On_change_champ() {
        $("[id*=div_id_condition]").hide();
        $("[id*=div_id_critere]").hide();
        var nom_champ = $(this).val();
        var type_champ = dict_champs[nom_champ].type;
        if (type_champ in dict_types) {
            $("#div_id_" + dict_types[type_champ].condition).show();
            $("#id_" + dict_types[type_champ].condition).trigger("change");
        };
    }
    
    $("#id_condition1, #id_condition2, #id_condition3, #id_condition4, #id_condition5, #id_condition6").on("change", function(event){
        $("[id*=div_id_critere]").hide();
        var nom_champ = $("#id_champ").val();
        var type_champ = dict_champs[nom_champ].type;
        var liste_ctrl = dict_types[type_champ].criteres;
        var nom_condition = $(this).val();
        dict_types[type_champ].criteres[nom_condition].forEach(function(ctrl) {
            $("#div_id_" + ctrl).show();
        });
    });
    $(document).ready(function() {
        $('#id_champ').change(On_change_champ);
        On_change_champ.call($('#id_champ').get(0));
    });
    
</script>
"""
