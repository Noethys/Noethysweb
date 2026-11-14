# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views.mydatatableview import MyDatatable, columns
from core.views import crud
from core.models import TypeCongeCollaborateur, DemandeAbsenceCollaborateur
from parametrage.forms.types_conges_collaborateurs import Formulaire


class Page(crud.Page):
    model = TypeCongeCollaborateur
    url_liste = "types_conges_collaborateurs_liste"
    url_ajouter = "types_conges_collaborateurs_ajouter"
    url_modifier = "types_conges_collaborateurs_modifier"
    url_supprimer = "types_conges_collaborateurs_supprimer"
    description_liste = "Les types de congés définissent les compteurs suivis pour les collaborateurs (congés annuels, RTT, récupération...). " \
                        "Chaque type est relié à une catégorie d'évènements du planning : les évènements de cette catégorie sont décomptés du solde."
    description_saisie = "Saisissez les caractéristiques du type de congé puis cliquez sur le bouton Enregistrer."
    objet_singulier = "un type de congé"
    objet_pluriel = "des types de congés"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = TypeCongeCollaborateur

    def get_queryset(self):
        return TypeCongeCollaborateur.objects.select_related("categorie").filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idtype_conge", "nom"]
        categorie = columns.TextColumn("Catégorie d'évènements", sources=["categorie__nom"], processor="Get_categorie")
        unite = columns.TextColumn("Unité", sources=["unite"], processor="Get_unite")
        periode = columns.TextColumn("Période de référence", sources=["mois_debut"], processor="Get_periode")
        actif = columns.TextColumn("Actif", sources=["actif"], processor="Get_actif")
        actions = columns.TextColumn("Actions", sources=None, processor="Get_actions_standard")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idtype_conge", "nom", "categorie", "unite", "periode", "actif"]
            ordering = ["ordre", "nom"]

        def Get_categorie(self, instance, *args, **kwargs):
            return """<i class="fa fa-circle margin-r-5" style="color: %s"></i> %s""" % (instance.categorie.couleur, instance.categorie.nom)

        def Get_unite(self, instance, *args, **kwargs):
            return instance.get_unite_display()

        def Get_periode(self, instance, *args, **kwargs):
            return "Année civile" if instance.mois_debut == 1 else "De %s à %s" % (instance.get_mois_debut_display().lower(), dict(TypeCongeCollaborateur._meta.get_field("mois_debut").choices)[(instance.mois_debut + 10) % 12 + 1].lower())

        def Get_actif(self, instance, *args, **kwargs):
            return "Oui" if instance.actif else "Non"


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    def Check_protections(self, objet=None):
        protections = []
        if DemandeAbsenceCollaborateur.objects.filter(type_conge=objet).exists():
            protections.append("Des demandes d'absence sont associées à ce type de congé. vous pouvez le désactiver")
        return protections
