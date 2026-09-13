# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, datetime
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.db.models import Q, Exists, OuterRef
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Piece
from core.utils import utils_dates
from individus.forms.pieces_fournies_modifier_lot import Formulaire
from individus.forms.liste_pieces_fournies_purger import Formulaire_purge


def Modifier_lot(request):
    """ Appliquer une action """
    liste_pk = json.loads(request.POST["liste_pieces"])

    form = Formulaire(json.loads(request.POST.get("form_modifier")))
    if not form.is_valid():
        messages_erreurs = ["%s : %s" % (field.title(), erreur[0].message) for field, erreur in form.errors.as_data().items()]
        return JsonResponse({"erreur": messages_erreurs}, status=401)

    # Importation des pièces
    liste_pieces = Piece.objects.filter(pk__in=liste_pk)

    # Sélection des modifications à appliquer
    modifications = {}
    if form.cleaned_data["choix_date_debut"] != "PAS_MODIFIER":
        modifications["date_debut"] = form.cleaned_data["date_debut"]
    if form.cleaned_data["choix_date_fin"] != "PAS_MODIFIER":
        modifications["date_fin"] = form.cleaned_data["date_fin"]

    # Application des modifications dans chaque pièce
    liste_pieces.update(**modifications)

    return JsonResponse({"resultat": "ok"})


class Page(crud.Page):
    model = Piece
    url_liste = "liste_pieces_fournies"
    description_liste = "Voici ci-dessous la liste des pièces fournies. Vous pouvez ici cocher des pièces pour les supprimer ou les modifier par lot."
    objet_singulier = "une pièce fournie"
    objet_pluriel = "des pièces fournies"
    url_supprimer_plusieurs = "pieces_supprimer_plusieurs"
    boutons_liste = [
        {"label": "Purger les pièces obsolètes", "classe": "btn btn-warning", "href": reverse_lazy("pieces_purger"), "icone": "fa fa-trash-o"},
    ]


def Get_condition_remplacees():
    """ Condition Q correspondant aux pièces remplacées par au moins une pièce plus récente de même type pour le même individu ou la même famille """
    plus_recente = Piece.objects.filter(type_piece_id=OuterRef("type_piece_id"), date_debut__gt=OuterRef("date_debut")).filter(
        Q(individu_id=OuterRef("individu_id")) | Q(famille_id=OuterRef("famille_id"))
    )
    return Exists(plus_recente)


def Get_condition_purge(purger_perimees=False, date_perimees=None, purger_remplacees=False):
    """ Construit la condition Q correspondant au cumul des critères de purge cochés """
    conditions = Q()
    if purger_perimees:
        conditions |= Q(date_fin__isnull=False, date_fin__lt=date_perimees)
    if purger_remplacees:
        conditions |= Q(pk__in=Piece.objects.annotate(remplacee=Get_condition_remplacees()).filter(remplacee=True).values_list("pk", flat=True))
    return conditions


class Liste(Page, crud.Liste):
    template_name = "individus/liste_pieces_fournies.html"

    def get_queryset(self):
        return Piece.objects.select_related("famille", "individu", "type_piece").filter(self.Get_filtres("Q")).annotate(remplacee=Get_condition_remplacees())

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['active_checkbox'] = True
        context['boutons_coches'] = json.dumps([
            {"id": "bouton_modifier", "action": "afficher_modal_modifier()", "title": "Modifier", "label": "<i class='fa fa-pencil margin-r-5'></i>Modifier"},
        ])
        context['form_modifier'] = Formulaire()
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:famille", "igenerique:individu", "idpiece", "date_debut", "date_fin", "type_piece__nom", "titre"]
        check = columns.CheckBoxSelectColumn(label="")
        type_piece = columns.TextColumn("Type de pièce", sources=["type_piece__nom"])
        document = columns.TextColumn("Document", sources=[], processor='Get_document')
        etat = columns.TextColumn("Etat", sources=['date_fin', 'remplacee'], processor='Get_etat')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', "idpiece", "date_debut", "date_fin", "type_piece", "titre", "famille", "individu", "document", "etat", "observations"]
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            hidden_columns = ["observations"]
            ordering = ["date_debut"]

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
            if not instance.famille_id:
                return []
            html = [
                self.Create_bouton_modifier(url=reverse("famille_pieces_modifier", kwargs={"idfamille": instance.famille_id, "pk": instance.pk})),
                self.Create_bouton_supprimer(url=reverse("famille_pieces_supprimer", kwargs={"idfamille": instance.famille_id, "pk": instance.pk})),
                self.Create_bouton(url=reverse("famille_resume", args=[instance.famille_id]), title="Ouvrir la fiche famille", icone="fa-users"),
            ]
            return self.Create_boutons_actions(html)


class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
    pass


class Purger(Page, TemplateView):
    template_name = "individus/liste_pieces_fournies_purger.html"
    form_class = Formulaire_purge

    def get_context_data(self, **kwargs):
        context = super(Purger, self).get_context_data(**kwargs)
        context['page_titre'] = "Purger les pièces obsolètes"
        context['box_titre'] = "Purger les pièces obsolètes"
        context['box_introduction'] = "Sélectionnez le ou les critères de purge souhaités et cliquez sur le bouton Purger. Cochez au moins un des deux critères. Si vous cochez les deux, une pièce sera supprimée dès qu'elle correspond à l'un ou l'autre des critères. <b>Attention, cette opération est irréversible.</b> La liste des pièces concernées vous sera présentée pour confirmation avant toute suppression."
        context['form'] = context.get("form", self.form_class())
        return context

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        conditions = Get_condition_purge(**form.cleaned_data)

        pieces_a_purger = Piece.objects.filter(conditions)
        nombre = pieces_a_purger.count()
        pieces_a_purger.delete()

        if nombre:
            messages.add_message(self.request, messages.SUCCESS, "%d pièce(s) supprimée(s) avec succès." % nombre)
        else:
            messages.add_message(self.request, messages.WARNING, "Aucune pièce ne correspond aux critères sélectionnés.")

        return HttpResponseRedirect(reverse_lazy("liste_pieces_fournies"))


def Previsualiser_purge(request):
    """ Renvoie la liste des pièces qui seraient supprimées par la purge, pour affichage dans la modal de confirmation """
    form = Formulaire_purge(request.POST)
    if not form.is_valid():
        premier_message = list(form.errors.values())[0][0] if form.errors else "Le formulaire n'est pas valide."
        return JsonResponse({"erreur": premier_message}, status=401)

    conditions = Get_condition_purge(**form.cleaned_data)
    queryset = Piece.objects.filter(conditions).select_related("individu", "famille", "type_piece").order_by("type_piece__nom", "date_debut")

    lignes = []
    for piece in queryset:
        lignes.append({
            "individu": piece.individu.Get_nom() if piece.individu else (piece.famille.nom if piece.famille else ""),
            "type_piece": str(piece.type_piece) if piece.type_piece else "",
            "date_debut": utils_dates.ConvertDateToFR(piece.date_debut) if piece.date_debut else "",
            "date_fin": utils_dates.ConvertDateToFR(piece.date_fin) if piece.date_fin else "",
        })

    return JsonResponse({"nombre": len(lignes), "lignes": lignes})
