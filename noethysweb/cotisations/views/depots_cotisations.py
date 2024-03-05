# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import DepotCotisations, Cotisation, FiltreListe
from core.utils import utils_texte, utils_preferences
from cotisations.forms.depots_cotisations import Formulaire


class Page(crud.Page):
    model = DepotCotisations
    url_liste = "depots_cotisations_liste"
    url_ajouter = "depots_cotisations_ajouter"
    url_modifier = "depots_cotisations_modifier"
    url_supprimer = "depots_cotisations_supprimer"
    url_consulter = "depots_cotisations_consulter"
    description_liste = "Voici ci-dessous la liste des dépôts d'adhésions."
    description_saisie = "Saisissez toutes les informations concernant le dépôt à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un dépôt d'adhésions"
    objet_pluriel = "des dépôts d'adhésions"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = DepotCotisations

    def get_queryset(self):
        return DepotCotisations.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["iddepot", 'verrouillage', 'date', 'nom', 'quantite', 'observations']
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        verrouillage = columns.TextColumn("Verrouillage", sources=["montant"], processor='Get_verrouillage')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['iddepot', 'verrouillage', 'date', 'nom', 'quantite', 'observations']
            processors = {
                "date": helpers.format_date("%d/%m/%Y"),
                "montant": "Formate_montant",
            }
            ordering = ["date"]

        def Formate_montant(self, instance, **kwargs):
            return "%0.2f %s" % (instance.montant or 0.0, utils_preferences.Get_symbole_monnaie())

        def Get_verrouillage(self, instance, **kwargs):
            if instance.verrouillage:
                return "<span class='text-green'><i class='fa fa-lock margin-r-5'></i> Verrouillé</span>"
            else:
                return "<span class='text-red'><i class='fa fa-unlock margin-r-5'></i> Non verrouillé</span>"

        def Get_actions_speciales(self, instance, *args, **kwargs):
            view = kwargs["view"]
            html = [
                self.Create_bouton_modifier(url=reverse(view.url_consulter, args=[instance.pk])),
                self.Create_bouton_supprimer(url=reverse(view.url_supprimer, args=[instance.pk])),
            ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={'pk': self.object.iddepot})


class Modifier(Page, crud.Modifier):
    form_class = Formulaire

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={'pk': self.kwargs['pk']})


class Supprimer(Page, crud.Supprimer):
    pass


class Consulter(Page, crud.Liste):
    template_name = "cotisations/depots_cotisations.html"
    mode = "CONSULTATION"
    model = Cotisation
    boutons_liste = []
    url_supprimer_plusieurs = "depots_cotisations_supprimer_plusieurs_cotisations"

    def get_queryset(self):
        return Cotisation.objects.select_related('famille', 'individu', 'type_cotisation', 'type_cotisation__structure', 'unite_cotisation', 'depot_cotisation').filter(self.Get_filtres("Q"), depot_cotisation_id=self.kwargs["pk"])

    def Get_stats(self, iddepot=None):
        quantite = Cotisation.objects.filter(depot_cotisation_id=iddepot).count()
        if not quantite:
            texte = "<b>Aucune adhésion incluse</b> : Cliquez sur 'Ajouter des adhésions' pour commencer..."
        else:
            texte = "<b>%d adhésions</b>" % quantite
        return texte

    def get_context_data(self, **kwargs):
        context = super(Consulter, self).get_context_data(**kwargs)
        context['box_titre'] = "Consulter un dépot"
        context['box_introduction'] = "Vous pouvez ici ajouter des adhésions au dépot ou modifier les paramètres du dépôt."
        context['onglet_actif'] = "depots_cotisations_liste"
        context['active_checkbox'] = True
        context['url_supprimer_plusieurs'] = reverse_lazy(self.url_supprimer_plusieurs, kwargs={"iddepot": self.kwargs["pk"], "listepk": "xxx"})
        context['depot'] = DepotCotisations.objects.get(pk=self.kwargs["pk"])
        context["stats"] = self.Get_stats(iddepot=self.kwargs["pk"])
        return context

    class datatable_class(MyDatatable):
        filtres = ["igenerique:individu", "fgenerique:famille", "idcotisation", "date_saisie", "date_creation_carte", "numero",
                   "date_debut", "date_fin", "observations", "type_cotisation__nom", "unite_cotisation__nom"]
        check = columns.CheckBoxSelectColumn(label="")
        individu = columns.CompoundColumn("Individu", sources=['individu__nom', 'individu__prenom'])
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        nom_cotisation = columns.TextColumn("Nom", sources=['type_cotisation__nom', 'unite_cotisation__nom'], processor='Get_nom_cotisation')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idcotisation", "date_debut", "date_fin", "famille", "individu", "nom_cotisation", "numero", "actions"]
            processors = {
                "date_debut": helpers.format_date("%d/%m/%Y"),
                "date_fin": helpers.format_date("%d/%m/%Y"),
            }
            labels = {
                "date_debut": "Début",
                "date_fin": "Fin",
            }
            ordering = ["-idcotisation"]

        def Get_nom_cotisation(self, instance, *args, **kwargs):
            if instance.prestation:
                return instance.prestation.label
            else:
                return "%s - %s" % (instance.type_cotisation.nom, instance.unite_cotisation.nom)

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_supprimer(url=reverse("depots_cotisations_supprimer_cotisation", kwargs={"iddepot": instance.depot_cotisation_id, "pk": instance.pk})),
            ]
            return self.Create_boutons_actions(html)

        def Formate_montant(self, instance, **kwargs):
            return utils_texte.Formate_montant(instance.montant)


class Supprimer_cotisation(Page, crud.Supprimer):
    model = Cotisation
    objet_singulier = "une adhésion"

    def delete(self, request, *args, **kwargs):
        # Modification du dépôt de cette cotisation
        cotisation = self.get_object()
        cotisation.depot_cotisation = None
        cotisation.save()

        # Enregistrement de la nouvelle quantité du dépôt
        DepotCotisations.objects.get(pk=self.kwargs["iddepot"]).Maj_quantite()

        # Confirmation de la suppression
        messages.add_message(self.request, messages.SUCCESS, 'Suppression effectuée avec succès')
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={"pk": self.kwargs["iddepot"]})


class Supprimer_plusieurs_cotisations(Page, crud.Supprimer_plusieurs):
    model = Cotisation
    objet_pluriel = "des adhésions"

    def post(self, request, **kwargs):
        # Modification du dépôt de ces adhésions
        for cotisation in self.get_objets():
            cotisation.depot_cotisation = None
            cotisation.save()

        # Enregistrement de la nouvelle quantité du dépôt
        DepotCotisations.objects.get(pk=self.kwargs["iddepot"]).Maj_quantite()

        # Confirmation de la suppression
        messages.add_message(self.request, messages.SUCCESS, 'Suppressions effectuées avec succès')
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={"pk": self.kwargs["iddepot"]})
