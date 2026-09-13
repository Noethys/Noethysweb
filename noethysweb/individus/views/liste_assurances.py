# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.urls import reverse_lazy, reverse
from django.views.generic import TemplateView
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib import messages
from django.db.models import Q, Exists, OuterRef
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Assurance
from core.utils import utils_dates
from individus.forms.liste_assurances import Formulaire_purge


class Page(crud.Page):
    model = Assurance
    url_liste = "liste_assurances"
    url_supprimer = "assurances_supprimer"
    url_supprimer_plusieurs = "assurances_supprimer_plusieurs"
    description_liste = "Voici ci-dessous la liste des assurances de tous les individus."
    objet_singulier = "une assurance"
    objet_pluriel = "des assurances"
    boutons_liste = [
        {"label": "Purger les assurances obsolètes", "classe": "btn btn-warning", "href": reverse_lazy("assurances_purger"), "icone": "fa fa-trash-o"},
    ]


def Get_condition_remplacees():
    """ Condition Q correspondant aux assurances remplacées par au moins une assurance plus récente pour le même individu """
    plus_recente = Assurance.objects.filter(individu_id=OuterRef("individu_id"), date_debut__gt=OuterRef("date_debut"))
    return Exists(plus_recente)


def Get_condition_purge(purger_perimees=False, date_perimees=None, purger_remplacees=False):
    """ Construit la condition Q correspondant au cumul des critères de purge cochés """
    conditions = Q()
    if purger_perimees:
        conditions |= Q(date_fin__isnull=False, date_fin__lt=date_perimees)
    if purger_remplacees:
        conditions |= Q(pk__in=Assurance.objects.annotate(remplacee=Get_condition_remplacees()).filter(remplacee=True).values_list("pk", flat=True))
    return conditions


class Liste(Page, crud.Liste):
    model = Assurance

    def get_queryset(self):
        return Assurance.objects.select_related("individu", "famille", "assureur").filter(self.Get_filtres("Q")).annotate(remplacee=Get_condition_remplacees())

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['page_titre'] = "Assurances"
        context['box_titre'] = "Liste des assurances"
        context['active_checkbox'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["igenerique:individu", "fgenerique:famille", "idassurance", "assureur__nom", "date_debut", "date_fin"]
        check = columns.CheckBoxSelectColumn(label="")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        individu = columns.TextColumn("Individu", sources=['individu__nom', 'individu__prenom'], processor="Formate_individu")
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        assureur = columns.TextColumn("Assureur", sources=['assureur__nom'])
        num_contrat = columns.TextColumn("N° de contrat", sources=[], processor='Get_num_contrat')
        document = columns.TextColumn("Document", sources=[], processor='Get_document')
        etat = columns.TextColumn("Etat", sources=['date_fin', 'remplacee'], processor='Get_etat')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', "idassurance", "individu", "famille", "assureur", "num_contrat", "date_debut", "date_fin", "document", "etat"]
            ordering = ["-date_debut"]
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }

        def Formate_individu(self, instance, **kwargs):
            return instance.individu.Get_nom() if instance.individu else ""

        def Get_num_contrat(self, instance, **kwargs):
            return instance.num_contrat

        def Get_document(self, instance, **kwargs):
            if instance.document:
                return self.Create_bouton(url=instance.document.url, title="Afficher le document", icone="fa-file-o", args='target="_blank"')
            return ""

        def Get_etat(self, instance, *args, **kwargs):
            if instance.date_fin and instance.date_fin < datetime.date.today():
                return "<small class='badge badge-danger'>Expirée</small>"
            if instance.remplacee:
                return "<small class='badge badge-warning'>Remplacée</small>"
            return "<small class='badge badge-success'>En cours</small>"

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.pk])),
                self.Create_bouton(url=reverse("individu_assurances_liste", args=[instance.famille_id, instance.individu_id]), title="Ouvrir la fiche individuelle", icone="fa-user"),
            ]
            return self.Create_boutons_actions(html)


class Supprimer(Page, crud.Supprimer):
    pass


class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
    pass


class Purger(Page, TemplateView):
    template_name = "individus/liste_assurances_purger.html"
    form_class = Formulaire_purge

    def get_context_data(self, **kwargs):
        context = super(Purger, self).get_context_data(**kwargs)
        context['page_titre'] = "Purger les assurances obsolètes"
        context['box_titre'] = "Purger les assurances obsolètes"
        context['box_introduction'] = "Sélectionnez le ou les critères de purge souhaités et cliquez sur le bouton Purger. Cochez au moins un des deux critères. Si vous cochez les deux, une assurance sera supprimée dès qu'elle correspond à l'un ou l'autre des critères. <b>Attention, cette opération est irréversible.</b> La liste des assurances concernées vous sera présentée pour confirmation avant toute suppression."
        context['form'] = context.get("form", self.form_class())
        return context

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        conditions = Get_condition_purge(**form.cleaned_data)

        assurances_a_purger = Assurance.objects.filter(conditions)
        nombre = assurances_a_purger.count()
        assurances_a_purger.delete()

        if nombre:
            messages.add_message(self.request, messages.SUCCESS, "%d assurance(s) supprimée(s) avec succès." % nombre)
        else:
            messages.add_message(self.request, messages.WARNING, "Aucune assurance ne correspond aux critères sélectionnés.")

        return HttpResponseRedirect(reverse_lazy("liste_assurances"))


def Previsualiser_purge(request):
    """ Renvoie la liste des assurances qui seraient supprimées par la purge, pour affichage dans la modal de confirmation """
    form = Formulaire_purge(request.POST)
    if not form.is_valid():
        premier_message = list(form.errors.values())[0][0] if form.errors else "Le formulaire n'est pas valide."
        return JsonResponse({"erreur": premier_message}, status=401)

    conditions = Get_condition_purge(**form.cleaned_data)
    queryset = Assurance.objects.filter(conditions).select_related("individu", "assureur").order_by("individu__nom", "individu__prenom", "date_debut")

    lignes = []
    for assurance in queryset:
        lignes.append({
            "individu": assurance.individu.Get_nom() if assurance.individu else "",
            "assureur": str(assurance.assureur) if assurance.assureur else "",
            "date_debut": utils_dates.ConvertDateToFR(assurance.date_debut) if assurance.date_debut else "",
            "date_fin": utils_dates.ConvertDateToFR(assurance.date_fin) if assurance.date_fin else "",
        })

    return JsonResponse({"nombre": len(lignes), "lignes": lignes})
