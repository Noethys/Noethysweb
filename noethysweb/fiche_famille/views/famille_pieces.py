# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Famille, Individu, Piece, TypePiece, Inscription, Rattachement
from fiche_famille.forms.famille_pieces import Formulaire
from fiche_famille.views.famille import Onglet
import datetime
from django.views.generic.base import RedirectView
from django.contrib import messages
from individus.utils import utils_pieces_manquantes
from django.db.models import Q


class Page(Onglet):
    model = Piece
    url_liste = "famille_pieces_liste"
    url_ajouter = "famille_pieces_ajouter"
    url_modifier = "famille_pieces_modifier"
    url_supprimer = "famille_pieces_supprimer"
    url_supprimer_plusieurs = "famille_pieces_supprimer_plusieurs"
    description_liste = "Consultez et saisissez ici les pièces de la famille."
    description_saisie = "Saisissez toutes les informations concernant la pièce et cliquez sur le bouton Enregistrer."
    objet_singulier = "une pièce"
    objet_pluriel = "des pièces"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        if not hasattr(self, "verbe_action"):
            context['box_titre'] = "Pièces"
        context['onglet_actif'] = "pieces"
        context['pieces_fournir'] = utils_pieces_manquantes.Get_pieces_manquantes(famille=context['famille'], utilisateur=self.request.user)
        if self.request.user.has_perm("core.famille_pieces_modifier"):
            context['boutons_liste'] = [
                {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'idfamille': self.kwargs.get('idfamille', None)}), "icone": "fa fa-plus"},
            ]
        context['bouton_supprimer'] = self.request.user.has_perm("core.famille_pieces_modifier")
        # Ajout l'idfamille à l'URL de suppression groupée
        context['url_supprimer_plusieurs'] = reverse_lazy(self.url_supprimer_plusieurs, kwargs={'idfamille': self.kwargs.get('idfamille', None), "listepk": "xxx"})
        return context

    def test_func_page(self):
        if getattr(self, "verbe_action", None) in ("Ajouter", "Modifier", "Supprimer") and not self.request.user.has_perm("core.famille_pieces_modifier"):
            return False
        return True

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idindividu au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idfamille"] = self.Get_idfamille()
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idfamille': self.kwargs.get('idfamille', None)})



class Liste(Page, crud.Liste):
    model = Piece
    template_name = "fiche_famille/famille_pieces.html"

    def get_queryset(self):
        inscriptions = Inscription.objects.filter(famille_id=self.Get_idfamille())
        liste = Piece.objects.select_related('individu', 'type_piece').filter((Q(famille_id=self.Get_idfamille()) | Q(individu_id__in=[i.individu_id for i in inscriptions], type_piece__valide_rattachement=True)) & self.Get_filtres("Q"))
        return liste

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['active_checkbox'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ['idpiece', 'date_debut', 'date_fin', "auteur"]

        check = columns.CheckBoxSelectColumn(label="")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        nom = columns.TextColumn("Nom de la pièce", sources=None, processor='Get_nom')
        date_fin = columns.TextColumn("Date de fin", sources=["date_fin"], processor='Get_date_fin')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', 'idpiece', 'date_debut', 'date_fin', 'nom', "auteur"]
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ['date_debut']

        def Get_nom(self, instance, **kwargs):
            return instance.Get_nom()

        def Get_date_fin(self, instance, **kwargs):
            if instance.date_fin == datetime.date(2999, 1, 1):
                return "Illimitée"
            else:
                return instance.date_fin.strftime('%d/%m/%Y')

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idindividu dans les boutons d'actions """
            view = kwargs["view"]
            if not view.request.user.has_perm("core.famille_pieces_modifier"):
                return "<span class='text-red' title='Accès interdit'><i class='fa fa-lock'></i></span>"
            kwargs = view.kwargs
            kwargs["pk"] = instance.pk
            html = [
                self.Create_bouton_modifier(url=reverse(view.url_modifier, kwargs=kwargs)),
                self.Create_bouton_supprimer(url=reverse(view.url_supprimer, kwargs=kwargs)),
            ]
            return self.Create_boutons_actions(html)



class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "fiche_famille/famille_edit.html"


class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "fiche_famille/famille_edit.html"


class Supprimer(Page, crud.Supprimer):
    template_name = "fiche_famille/famille_delete.html"


class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
    template_name = "fiche_famille/famille_delete.html"


class Saisie_rapide(Page, RedirectView):
    """ Saisie rapide d'une pièce"""
    def get_redirect_url(self, *args, **kwargs):
        if not self.request.user.has_perm("core.famille_pieces_modifier"):
            messages.add_message(self.request, messages.ERROR, "Vous n'avez pas l'autorisation de modifier cette page")
            return self.request.META['HTTP_REFERER']

        type_piece = TypePiece.objects.get(pk=kwargs["idtype_piece"])
        individu = Individu.objects.get(pk=kwargs["idindividu"])
        famille = Famille.objects.get(pk=kwargs["idfamille"])

        # Famille
        if type_piece.public == "famille":
            individu = None

        # Individu
        if type_piece.public == "individu" and type_piece.valide_rattachement:
            famille = None

        # Validité
        date_debut = datetime.date.today()
        date_fin = type_piece.Get_date_fin_validite()

        # Enregistrement de la pièce
        piece = Piece.objects.create(type_piece=type_piece, individu=individu, famille=famille, date_debut=date_debut, date_fin=date_fin, auteur=self.request.user)
        messages.add_message(self.request, messages.SUCCESS, "La pièce '%s' a été créée avec succès" % piece.Get_nom())
        return self.request.META['HTTP_REFERER']
