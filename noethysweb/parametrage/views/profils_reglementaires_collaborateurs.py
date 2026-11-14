# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.db.models import Count
from core.views.mydatatableview import MyDatatable, columns
from core.views import crud
from core.models import ProfilReglementaireCollaborateur
from collaborateurs.utils.utils_controle_reglementaire import REGLES, Format_valeur_regle
from parametrage.forms.profils_reglementaires_collaborateurs import Formulaire


class Page(crud.Page):
    model = ProfilReglementaireCollaborateur
    url_liste = "profils_reglementaires_collaborateurs_liste"
    url_ajouter = "profils_reglementaires_collaborateurs_ajouter"
    url_modifier = "profils_reglementaires_collaborateurs_modifier"
    url_supprimer = "profils_reglementaires_collaborateurs_supprimer"
    description_liste = "Les profils réglementaires définissent les règles de temps de travail contrôlées dans le planning général et le planning individuel (durée maximale, amplitude, repos, pauses...). " \
                        "Chaque contrat peut indiquer son profil ; à défaut, le profil par défaut s'applique. Les anomalies sont signalées sans bloquer l'enregistrement."
    description_saisie = "Saisissez le nom du profil et les valeurs des règles à contrôler (laissez une règle vide pour la désactiver), puis cliquez sur le bouton Enregistrer."
    objet_singulier = "un profil réglementaire"
    objet_pluriel = "des profils réglementaires"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = ProfilReglementaireCollaborateur

    def get_queryset(self):
        return ProfilReglementaireCollaborateur.objects.filter(self.Get_filtres("Q")).annotate(nbre_contrats=Count("contrats"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idprofil", "nom"]
        nom = columns.TextColumn("Nom", sources=["nom"], processor="Get_nom")
        regles = columns.TextColumn("Règles contrôlées", sources=None, processor="Get_regles")
        nbre_contrats = columns.TextColumn("Contrats associés", sources="nbre_contrats")
        actions = columns.TextColumn("Actions", sources=None, processor="Get_actions_standard")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idprofil", "nom", "regles", "nbre_contrats"]
            ordering = ["nom"]

        def Get_nom(self, instance, *args, **kwargs):
            return "%s%s" % (instance.nom, " <span class='badge badge-info'>Par défaut</span>" if instance.defaut else "")

        def Get_regles(self, instance, *args, **kwargs):
            textes = ["%s %s" % (regle["court"], Format_valeur_regle(regle["code"], getattr(instance, regle["code"])))
                      for regle in REGLES if getattr(instance, regle["code"]) is not None]
            if instance.pause_duree and instance.pause_apres:
                textes.append("Pause %s après %s" % (Format_valeur_regle("pause_duree", instance.pause_duree), Format_valeur_regle("pause_apres", instance.pause_apres)))
            return " · ".join(textes) or "Aucune règle"


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    pass
