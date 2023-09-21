# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.contrib import messages
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import ComptaReleve, ComptaOperation
from core.utils import utils_texte
from comptabilite.forms.rapprochements import Formulaire


class Page(crud.Page):
    model = ComptaReleve
    url_liste = "rapprochements_liste"
    url_ajouter = "rapprochements_ajouter"
    url_modifier = "rapprochements_modifier"
    url_supprimer = "rapprochements_supprimer"
    url_consulter = "rapprochements_consulter"
    description_liste = "Vous pouvez ici effectuer du rapprochement bancaire. Cliquez sur Ajouter pour créer un nouveau relevé de compte ou cliquez sur Modifier pour accéder au détail du relevé."
    objet_singulier = "un rapprochement bancaire"
    objet_pluriel = "des rapprochements bancaires"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['page_titre'] = "Rapprochement bancaire"
        return context

class Liste(Page, crud.Liste):
    model = ComptaReleve

    def get_queryset(self):
        return ComptaReleve.objects.filter(self.Get_filtres("Q")).annotate(nbre_operations=Count("comptaoperation"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['box_titre'] = "Liste des relevés bancaires"
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idreleve", "nom", "date_debut", "date_fin", "compte__nom"]
        nbre_operations = columns.TextColumn("Nbre", sources="nbre_operations")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idreleve", "nom", "date_debut", "date_fin", "compte", "nbre_operations", "actions"]
            processors = {
                "date_debut": helpers.format_date("%d/%m/%Y"),
                "date_fin": helpers.format_date("%d/%m/%Y"),
            }
            ordering = ["date_debut"]

        def Get_actions_speciales(self, instance, *args, **kwargs):
            view = kwargs["view"]
            html = [
                self.Create_bouton_modifier(url=reverse(view.url_consulter, args=[instance.pk])),
                self.Create_bouton_supprimer(url=reverse(view.url_supprimer, args=[instance.pk])),
            ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

    def get_context_data(self, **kwargs):
        context = super(Ajouter, self).get_context_data(**kwargs)
        context['box_titre'] = "Ajouter un relevé bancaire"
        return context

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={'pk': self.object.idreleve})


class Modifier(Page, crud.Modifier):
    form_class = Formulaire

    def get_context_data(self, **kwargs):
        context = super(Modifier, self).get_context_data(**kwargs)
        context['box_titre'] = "Modifier un relevé bancaire"
        return context
    
    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={'pk': self.kwargs['pk']})


class Supprimer(Page, crud.Supprimer):
    pass


class Consulter(Page, crud.Liste):
    template_name = "comptabilite/rapprochements.html"
    mode = "CONSULTATION"
    model = ComptaOperation
    boutons_liste = []
    url_supprimer_plusieurs = "rapprochements_supprimer_plusieurs_operations"

    def get_queryset(self):
        return ComptaOperation.objects.select_related("tiers", "mode").filter(self.Get_filtres("Q"), releve_id=self.kwargs["pk"])

    def Get_stats(self, idreleve=None):
        quantite = ComptaOperation.objects.filter(releve_id=idreleve).count()
        stats = ComptaOperation.objects.select_related('mode').values("mode__label").filter(releve_id=idreleve).annotate(nbre=Count("pk"))
        if not stats:
            texte = "<b>Aucune opération</b>"
        else:
            liste_details = ["%d %s" % (stat["nbre"], stat["mode__label"]) for stat in stats]
            texte = "<b>%d opérations</b> : %s." % (quantite, utils_texte.Convert_liste_to_texte_virgules(liste_details))
        return texte

    def get_context_data(self, **kwargs):
        context = super(Consulter, self).get_context_data(**kwargs)
        context['page_titre'] = "Rapprochement bancaire"
        context['box_titre'] = "Modifier un relevé bancaire"
        context['box_introduction'] = "Vous pouvez ici ajouter des opérations au relevé ou modifier les paramètres du relevé."
        context['onglet_actif'] = "rapprochements_liste"
        context['active_checkbox'] = True
        context['url_supprimer_plusieurs'] = reverse_lazy(self.url_supprimer_plusieurs, kwargs={"idreleve": self.kwargs["pk"], "listepk": "xxx"})
        context['releve'] = ComptaReleve.objects.get(pk=self.kwargs["pk"])
        context["stats"] = self.Get_stats(idreleve=self.kwargs["pk"])
        return context

    class datatable_class(MyDatatable):
        filtres = ["idoperation", "type", "date", "libelle", "mode", "releve", "num_piece", "debit", "credit", "montant"]
        check = columns.CheckBoxSelectColumn(label="")
        debit = columns.TextColumn("Débit", sources=["montant"], processor="Get_montant_debit")
        credit = columns.TextColumn("Crédit", sources=["montant"], processor="Get_montant_credit")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idoperation", "date", "libelle", "mode", "num_piece", "debit", "credit", "actions"]
            processors = {
                "date": helpers.format_date('%d/%m/%Y'),
            }
            labels = {
                "mode": "Mode",
                "num_piece": "N° Pièce",
                "releve": "Relevé",
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
            html = [
                self.Create_bouton_supprimer(url=reverse("rapprochements_supprimer_operation", kwargs={"idreleve": instance.releve_id, "pk": instance.pk})),
            ]
            return self.Create_boutons_actions(html)


class Supprimer_operation(Page, crud.Supprimer):
    model = ComptaOperation
    objet_singulier = "une opération"

    def delete(self, request, *args, **kwargs):
        # Modification du relevé de cette opération
        operation = self.get_object()
        operation.releve = None
        operation.save()

        # Confirmation de la suppression
        messages.add_message(self.request, messages.SUCCESS, 'Suppression effectuée avec succès')
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={"pk": self.kwargs["idreleve"]})


class Supprimer_plusieurs_operations(Page, crud.Supprimer_plusieurs):
    model = ComptaOperation
    objet_pluriel = "des opérations"

    def post(self, request, **kwargs):
        # Modification du relevé de ces opérations
        for operation in self.get_objets():
            operation.releve = None
            operation.save()

        # Confirmation de la suppression
        messages.add_message(self.request, messages.SUCCESS, 'Suppressions effectuées avec succès')
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={"pk": self.kwargs["idreleve"]})
