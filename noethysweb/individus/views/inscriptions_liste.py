# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Inscription
from fiche_individu.forms.individu_inscriptions import Formulaire
from django.db.models import Q


class Page(crud.Page):
    model = Inscription
    url_liste = "inscriptions_liste"
    url_modifier = "inscriptions_modifier"
    url_supprimer = "inscriptions_supprimer"
    url_supprimer_plusieurs = "inscriptions_supprimer_plusieurs"
    description_liste = "Voici ci-dessous la liste des inscriptions. Vous ne pouvez accéder qu'aux inscriptions associées à vos structures."
    description_saisie = "Saisissez toutes les informations concernant l'inscription à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une inscription"
    objet_pluriel = "des inscriptions"


class Liste(Page, crud.Liste):
    model = Inscription

    def get_queryset(self):
        condition = Q(activite__structure__in=self.request.user.structures.all())
        return Inscription.objects.select_related("famille", "individu", "groupe", "categorie_tarif", "activite", "activite__structure").filter(self.Get_filtres("Q"), condition)

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context["impression_introduction"] = ""
        context["impression_conclusion"] = ""
        context["afficher_menu_brothers"] = True
        context["active_checkbox"] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["igenerique:individu", "fgenerique:famille", "idinscription", "date_debut", "date_fin", "activite__nom", "groupe__nom", "statut", "categorie_tarif__nom"]
        check = columns.CheckBoxSelectColumn(label="")
        actions = columns.TextColumn("Actions", sources=None, processor="Get_actions_speciales")
        activite = columns.TextColumn("Activité", sources=["activite__nom"])
        groupe = columns.TextColumn("Groupe", sources=["groupe__nom"])
        categorie_tarif = columns.TextColumn("Catégorie de tarif", sources=["categorie_tarif__nom"])
        individu = columns.CompoundColumn("Individu", sources=["individu__nom", "individu__prenom"])
        famille = columns.TextColumn("Famille", sources=["famille__nom"])
        individu_ville = columns.TextColumn("Ville de l'individu", processor="Get_ville_individu")
        famille_ville = columns.TextColumn("Ville de la famille", processor="Get_ville_famille")
        mail_famille = columns.TextColumn("Email famille", processor='Get_mail_famille')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idinscription", "date_debut", "date_fin", "individu", "famille", "activite", "groupe", "categorie_tarif", "individu_ville", "famille_ville", "mail_famille", "statut"]
            hidden_columns = ["famille_ville", "mail_famille"]
            processors = {
                "date_debut": helpers.format_date("%d/%m/%Y"),
                "date_fin": helpers.format_date("%d/%m/%Y"),
                "statut": "Formate_statut",
            }
            labels = {
                "date_debut": "Début",
                "date_fin": "Fin",
            }
            ordering = ["individu"]

        def Formate_statut(self, instance, *args, **kwargs):
            if instance.statut == "attente":
                return "<i class='fa fa-hourglass-2 text-yellow'></i> Attente"
            elif instance.statut == "refus":
                return "<i class='fa fa-times-circle text-red'></i> Refus"
            else:
                return "<i class='fa fa-check-circle-o text-green'></i> Valide"

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idindividu dans les boutons d'actions """
            view = kwargs["view"]
            # Récupération idindividu et idfamille
            kwargs = view.kwargs
            # Ajoute l'id de la ligne
            kwargs["pk"] = instance.pk
            html = [
                self.Create_bouton_modifier(url=reverse(view.url_modifier, kwargs=kwargs)),
                self.Create_bouton_supprimer(url=reverse(view.url_supprimer, kwargs=kwargs)),
                self.Create_bouton(url=reverse("famille_resume", args=[instance.famille_id]), title="Ouvrir la fiche famille", icone="fa-users"),
            ]
            return self.Create_boutons_actions(html)

        def Get_ville_individu(self, instance, *args, **kwargs):
            return instance.individu.ville_resid

        def Get_ville_famille(self, instance, *args, **kwargs):
            return instance.famille.ville_resid

        def Get_mail_famille(self, instance, *args, **kwargs):
            return instance.famille.mail


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass

class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
    pass