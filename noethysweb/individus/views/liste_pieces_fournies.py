# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.urls import reverse
from django.http import JsonResponse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Piece
from individus.forms.pieces_fournies_modifier_lot import Formulaire


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


class Liste(Page, crud.Liste):
    template_name = "individus/liste_pieces_fournies.html"

    def get_queryset(self):
        return Piece.objects.select_related("famille", "individu", "type_piece").filter(self.Get_filtres("Q"))

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
        filtres = ["fgenerique:famille", "igenerique:individu", "idpiece", "date_debut", "date_fin", "type_piece__nom"]
        check = columns.CheckBoxSelectColumn(label="")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', "idpiece", "date_debut", "date_fin", "type_piece", "famille", "individu"]
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ["date_debut"]

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
