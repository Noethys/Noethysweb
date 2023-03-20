# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.db.models import Q
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import ComptaOperationBudgetaire, CompteBancaire
from comptabilite.forms.operations_budgetaires import Formulaire


class Page(crud.Page):
    model = ComptaOperationBudgetaire
    url_liste = "operations_budgetaires_liste"
    url_modifier = "operations_budgetaires_modifier"
    url_supprimer = "operations_budgetaires_supprimer"
    description_liste = "Voici ci-dessous la liste des opérations budgétaires."
    description_saisie = "Saisissez toutes les informations concernant l'opération à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une opération budgétaire"
    objet_pluriel = "des opérations budgétaires"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        if getattr(self, "type", None) == "debit":
            context["box_titre"] += " au débit"
        if getattr(self, "type", None) == "credit":
            context["box_titre"] += " au crédit"
        context["categorie"] = self.Get_categorie()
        context['label_categorie'] = "Compte"
        context['liste_categories'] = [(item.pk, item.nom) for item in CompteBancaire.objects.filter(Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)).order_by("nom")]
        if context['liste_categories']:
            context['boutons_liste'] = [
                {"label": "Ajouter un débit", "classe": "btn btn-success", "href": reverse_lazy("operations_budgetaires_ajouter_debit", kwargs={'categorie': self.Get_categorie()}), "icone": "fa fa-plus"},
                {"label": "Ajouter un crédit", "classe": "btn btn-default", "href": reverse_lazy("operations_budgetaires_ajouter_credit", kwargs={'categorie': self.Get_categorie()}), "icone": "fa fa-plus"},
            ]
        else:
            context['box_introduction'] = "Vous pouvez saisir ici des opérations budgétaires.<br><b>Vous devez avoir enregistré au moins un compte bancaire avant de pouvoir ajouter des opérations !</b>"
        return context

    def test_func_page(self):
        # Vérifie que l'utilisateur a une permission d'accéder à ce compte
        idcompte = self.Get_categorie()
        if idcompte and idcompte not in [compte.pk for compte in CompteBancaire.objects.filter(self.Get_condition_structure())]:
            return False
        return True

    def Get_categorie(self):
        idcompte = self.kwargs.get('categorie', None)
        if idcompte:
            return idcompte
        compte = CompteBancaire.objects.filter(self.Get_condition_structure()).order_by("nom")
        return compte[0].pk if compte else 0

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["categorie"] = self.Get_categorie()
        form_kwargs["type"] = getattr(self, "type", None)
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'categorie': self.Get_categorie()})


class Liste(Page, crud.Liste):
    model = ComptaOperationBudgetaire
    template_name = "core/crud/liste_avec_categorie.html"

    def get_queryset(self):
        return ComptaOperationBudgetaire.objects.select_related("analytique", "categorie").filter(Q(compte=self.Get_categorie()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idoperation_budgetaire", "type", "date", "libelle", "analytique", "categorie", "debit", "credit", "montant"]
        analytique = columns.TextColumn("Analytique", sources=["analytique__nom"])
        categorie = columns.TextColumn("Catégorie", sources=["categorie__nom"])
        debit = columns.TextColumn("Débit", sources=["montant"], processor="Get_montant_debit")
        credit = columns.TextColumn("Crédit", sources=["montant"], processor="Get_montant_credit")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idoperation_budgetaire", "date_budget", "analytique", "categorie", "libelle", "debit", "credit", "actions"]
            ordering = ["date_budget"]
            processors = {
                "date_budget": helpers.format_date('%d/%m/%Y'),
            }

        def Get_montant_debit(self, instance, **kwargs):
            if instance.type == "debit":
                return "%0.2f" % instance.montant
            return None

        def Get_montant_credit(self, instance, **kwargs):
            if instance.type == "credit":
                return "%0.2f" % instance.montant
            return None

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut la catégorie dans les boutons d'actions """
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.compte_id, instance.pk])),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.compte_id, instance.pk])),
            ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    type = "debit"


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    form_class = Formulaire
