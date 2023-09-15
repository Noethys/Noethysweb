# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Facture, Prestation
from core.utils import utils_texte
from fiche_famille.forms.famille_factures import Formulaire
from fiche_famille.views.famille import Onglet
from facturation.utils import utils_factures


class Page(Onglet):
    model = Facture
    url_modifier = "famille_factures_modifier"
    url_supprimer = "famille_factures_supprimer"
    url_supprimer_plusieurs = "famille_factures_supprimer_plusieurs"
    url_consulter = "famille_factures_consulter"
    objet_singulier = "une facture"
    objet_pluriel = "des factures"


class Consulter(Page, crud.Liste):
    template_name = "fiche_famille/famille_factures_consulter.html"
    mode = "CONSULTATION"
    model = Prestation
    boutons_liste = []
    url_supprimer_plusieurs = "famille_factures_supprimer_plusieurs_prestations"

    def get_queryset(self):
        return Prestation.objects.select_related("individu", "activite").filter(self.Get_filtres("Q"), facture_id=self.kwargs["pk"])

    def Get_stats(self, facture=None):
        texte = "<b>Total : %s</b>" % utils_texte.Formate_montant(facture.total)
        return texte

    def get_context_data(self, **kwargs):
        context = super(Consulter, self).get_context_data(**kwargs)
        context['box_titre'] = "Consulter une facture"
        context['box_introduction'] = "Vous pouvez ici ajouter ou retirer des prestations ou modifier les caractéristiques de la facture. La suppression des prestations ici entraîne juste le retrait de la facture mais pas leur suppression de la fiche famille."
        context['onglet_actif'] = "famille_factures_liste"
        context['active_checkbox'] = True
        context['url_supprimer_plusieurs'] = reverse_lazy(self.url_supprimer_plusieurs, kwargs={"idfamille": self.kwargs["idfamille"], "idfacture": self.kwargs["pk"], "listepk": "xxx"})
        context['facture'] = Facture.objects.get(pk=self.kwargs["pk"])
        context["stats"] = self.Get_stats(facture=context['facture'])
        return context

    class datatable_class(MyDatatable):
        filtres = ["idprestation", "date", "individu__nom", "activite__nom", "label", "montant"]
        check = columns.CheckBoxSelectColumn(label="")
        activite = columns.TextColumn("Activité", sources=['activite__nom'])
        label = columns.TextColumn("Label", sources=['label'])
        individu = columns.TextColumn("Individu", sources=["individu__nom", "individu__prenom"], processor="Formate_individu")
        montant = columns.TextColumn("Montant", sources=["montant"], processor="Formate_montant")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idprestation", "date", "individu", "activite", "label", "montant", "actions"]
            processors = {
                "date": helpers.format_date("%d/%m/%Y"),
                "montant": "Formate_montant",
            }
            ordering = ["date"]

        def Formate_individu(self, instance, **kwargs):
            return instance.individu.Get_nom() if instance.individu else ""

        def Formate_montant(self, instance, **kwargs):
            return utils_texte.Formate_montant(instance.montant)

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_supprimer(url=reverse("famille_factures_supprimer_prestation", kwargs={"idfamille": instance.famille_id, "idfacture": instance.facture_id, "pk": instance.pk})),
            ]
            return self.Create_boutons_actions(html)


class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "fiche_famille/famille_edit.html"

    def get_context_data(self, **kwargs):
        context = super(Modifier, self).get_context_data(**kwargs)
        context['box_titre'] = "Modifier les caractéristiques de la facture"
        context['box_introduction'] = "Modifiez les caractéristiques souhaitées et cliquez sur Enregistrer. A utiliser avec précaution."
        return context

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Modifier, self).get_form_kwargs(**kwargs)
        form_kwargs["idfamille"] = self.Get_idfamille()
        return form_kwargs

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={"idfamille": self.kwargs["idfamille"], "pk": self.kwargs["pk"]})


class Supprimer_prestation(Page, crud.Supprimer):
    model = Prestation
    objet_singulier = "une prestation"
    check_protections = False

    def delete(self, request, *args, **kwargs):
        # Modification de la prestation
        prestation = self.get_object()
        prestation.facture = None
        prestation.save()

        # Enregistrement des totaux de la facture
        utils_factures.Maj_total_factures(IDfacture=self.kwargs["idfacture"])

        # Confirmation de la suppression
        messages.add_message(self.request, messages.SUCCESS, "Suppression effectuée avec succès")
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={"idfamille": self.kwargs["idfamille"], "pk": self.kwargs["idfacture"]})


class Supprimer_plusieurs_prestations(Page, crud.Supprimer_plusieurs):
    model = Prestation
    objet_pluriel = "des prestations"
    check_protections = False

    def post(self, request, **kwargs):
        # Modification des prestations
        for prestation in self.get_objets():
            prestation.facture = None
            prestation.save()

        # Enregistrement des totaux de la facture
        utils_factures.Maj_total_factures(IDfacture=self.kwargs["idfacture"])

        # Confirmation de la suppression
        messages.add_message(self.request, messages.SUCCESS, "Suppressions effectuées avec succès")
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={"idfamille": self.kwargs["idfamille"], "pk": self.kwargs["idfacture"]})
