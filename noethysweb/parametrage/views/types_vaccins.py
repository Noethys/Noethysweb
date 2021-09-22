# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.db.models import Count
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import TypeVaccin
from parametrage.forms.types_vaccins import Formulaire


class Page(crud.Page):
    model = TypeVaccin
    url_liste = "types_vaccins_liste"
    url_ajouter = "types_vaccins_ajouter"
    url_modifier = "types_vaccins_modifier"
    url_supprimer = "types_vaccins_supprimer"
    description_liste = "Voici ci-dessous la liste des types de vaccins."
    description_saisie = "Saisissez toutes les informations concernant le type de vaccin à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un type de vaccin"
    objet_pluriel = "des types de vaccins"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = TypeVaccin

    def get_queryset(self):
        return TypeVaccin.objects.prefetch_related("types_maladies").filter(self.Get_filtres("Q")).annotate(nbre_vaccins=Count("vaccin"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idtype_vaccin", "nom"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        duree_validite = columns.DisplayColumn("Validité", sources="duree_validite", processor='Get_validite')
        types_maladies = columns.TextColumn("Maladies associées", sources=None, processor='Get_types_maladies')
        nbre_vaccins = columns.TextColumn("Vaccins associés", sources="nbre_vaccins")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idtype_vaccin", "nom", "duree_validite", "types_maladies", "nbre_vaccins"]
            ordering = ["nom"]

        def Get_types_maladies(self, instance, *args, **kwargs):
            return ", ".join([type_maladie.nom for type_maladie in instance.types_maladies.all().order_by("nom")])

        def Get_validite(self, instance, **kwargs):
            if instance.duree_validite == None:
                return "Illimitée"
            elif instance.duree_validite.startswith("j"):
                jours, mois, annees = instance.duree_validite.split("-")
                jours, mois, annees = int(jours[1:]), int(mois[1:]), int(annees[1:])
                liste_duree = []
                if annees > 0: liste_duree.append("%d années" % annees)
                if mois > 0: liste_duree.append("%d mois" % mois)
                if jours > 0: liste_duree.append("%d jours" % jours)
                return ", ".join(liste_duree)
            return ""


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass
