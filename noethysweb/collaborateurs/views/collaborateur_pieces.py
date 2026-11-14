# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.urls import reverse_lazy, reverse
from django.db.models import Q
from django.views.generic.base import RedirectView
from django.contrib import messages
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import PieceCollaborateur, TypePieceCollaborateur, Collaborateur
from collaborateurs.forms.collaborateur_pieces import Formulaire
from collaborateurs.views.collaborateur import Onglet
from collaborateurs.utils import utils_pieces_manquantes


class Page(Onglet):
    model = PieceCollaborateur
    url_liste = "collaborateur_pieces_liste"
    url_ajouter = "collaborateur_pieces_ajouter"
    url_modifier = "collaborateur_pieces_modifier"
    url_supprimer = "collaborateur_pieces_supprimer"
    url_supprimer_plusieurs = "collaborateur_pieces_supprimer_plusieurs"
    description_liste = "Saisissez ici les pièces du collaborateur."
    description_saisie = "Saisissez toutes les informations concernant la pièce et cliquez sur le bouton Enregistrer."
    objet_singulier = "une pièce"
    objet_pluriel = "des pièces"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        if not hasattr(self, "verbe_action"):
            context['box_titre'] = "Pièces"
        context['onglet_actif'] = "pieces"
        context['pieces_fournir'] = utils_pieces_manquantes.Get_pieces_manquantes(collaborateur=context["collaborateur"])
        context['boutons_liste'] = [
            {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={"idcollaborateur": self.kwargs.get("idcollaborateur", None)}), "icone": "fa fa-plus"},
        ]
        # Ajout l'idcollaborateur à l'URL de suppression groupée
        context['url_supprimer_plusieurs'] = reverse_lazy(self.url_supprimer_plusieurs, kwargs={"idcollaborateur": self.kwargs.get("idcollaborateur", None), "listepk": "xxx"})
        return context

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idcollaborateur"] = self.Get_idcollaborateur()
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={"idcollaborateur": self.kwargs.get("idcollaborateur", None)})


class Liste(Page, crud.Liste):
    model = PieceCollaborateur
    template_name = "collaborateurs/collaborateur_pieces.html"

    def get_queryset(self):
        liste = PieceCollaborateur.objects.select_related("type_piece").filter(Q(collaborateur_id=self.Get_idcollaborateur()), self.Get_filtres("Q"))
        return liste

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['active_checkbox'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idpiece", "date_debut", "date_fin"]
        check = columns.CheckBoxSelectColumn(label="")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        nom = columns.TextColumn("Nom de la pièce", sources=None, processor='Get_nom')
        date_fin = columns.TextColumn("Date de fin", sources=["date_fin"], processor='Get_date_fin')
        statut = columns.TextColumn("Statut", sources=["statut"], processor='Get_statut')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idpiece", "date_debut", "date_fin", "nom", "statut"]
            processors = {
                "date_debut": helpers.format_date('%d/%m/%Y'),
            }
            ordering = ['date_debut']

        def Get_nom(self, instance, **kwargs):
            return instance.Get_nom()

        def Get_date_fin(self, instance, **kwargs):
            if instance.date_fin == datetime.date(2999, 1, 1):
                return "Illimitée"
            else:
                return instance.date_fin.strftime('%d/%m/%Y')

        def Get_statut(self, instance, **kwargs):
            if instance.statut == "ATTENTE":
                return "<span class='badge badge-warning'>En cours de vérification</span><br><small>Transmise le %s</small>" % instance.date_depot.strftime("%d/%m/%Y") if instance.date_depot else "<span class='badge badge-warning'>En cours de vérification</span>"
            if instance.statut == "REFUSEE":
                return "<span class='badge badge-secondary'>Refusée</span>"
            return "<span class='badge badge-success'>Valide</span>"

        def Get_actions_speciales(self, instance, *args, **kwargs):
            view = kwargs["view"]
            kwargs = view.kwargs
            kwargs["pk"] = instance.pk
            html = [
                self.Create_bouton_modifier(url=reverse(view.url_modifier, kwargs=kwargs)),
                self.Create_bouton_supprimer(url=reverse(view.url_supprimer, kwargs=kwargs)),
            ]
            if instance.statut == "ATTENTE":
                # Pièce transmise depuis l'espace collaborateur : à accepter ou à refuser
                html.insert(0, self.Create_bouton(url=reverse("collaborateur_pieces_decider", kwargs={"idcollaborateur": kwargs["idcollaborateur"], "pk": instance.pk, "decision": "refuser"}),
                                                  title="Refuser la pièce transmise", icone="fa-ban"))
                html.insert(0, self.Create_bouton(url=reverse("collaborateur_pieces_decider", kwargs={"idcollaborateur": kwargs["idcollaborateur"], "pk": instance.pk, "decision": "accepter"}),
                                                  title="Accepter la pièce transmise", icone="fa-check"))
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "collaborateurs/collaborateur_edit.html"


class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "collaborateurs/collaborateur_edit.html"


class Supprimer(Page, crud.Supprimer):
    template_name = "collaborateurs/collaborateur_delete.html"


class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
    template_name = "collaborateurs/collaborateur_delete.html"


class Saisie_rapide(Page, RedirectView):
    """ Saisie rapide d'une pièce"""
    def get_redirect_url(self, *args, **kwargs):
        type_piece = TypePieceCollaborateur.objects.get(pk=kwargs["idtype_piece"])
        collaborateur = Collaborateur.objects.get(pk=kwargs["idcollaborateur"])

        # Validité
        date_debut = datetime.date.today()
        date_fin = type_piece.Get_date_fin_validite()

        # Enregistrement de la pièce
        piece = PieceCollaborateur.objects.create(type_piece=type_piece, collaborateur=collaborateur,
                                                  date_debut=date_debut, date_fin=date_fin)
        messages.add_message(self.request, messages.SUCCESS, "La pièce '%s' a été créée avec succès" % piece.Get_nom())
        return self.request.META['HTTP_REFERER']


class Decider(Page, RedirectView):
    """ Acceptation ou refus d'une pièce transmise depuis l'espace collaborateur """
    def get_redirect_url(self, *args, **kwargs):
        piece = PieceCollaborateur.objects.filter(pk=kwargs["pk"], collaborateur_id=kwargs["idcollaborateur"], statut="ATTENTE").first()
        if piece:
            piece.statut = "VALIDE" if kwargs["decision"] == "accepter" else "REFUSEE"
            piece.save()
            from core.utils import utils_historique
            from collaborateurs.utils import utils_espace_collaborateur
            utils_historique.Ajouter(titre="Acceptation d'une pièce" if piece.statut == "VALIDE" else "Refus d'une pièce", detail=piece.Get_nom(), utilisateur=self.request.user,
                                     collaborateur=piece.collaborateur_id, objet="Pièce", idobjet=piece.pk, classe="PieceCollaborateur")
            utils_espace_collaborateur.Notifier_piece(piece, request=self.request)
            messages.add_message(self.request, messages.SUCCESS, "La pièce '%s' a été %s" % (piece.Get_nom(), "acceptée" if piece.statut == "VALIDE" else "refusée"))
        return reverse("collaborateur_pieces_liste", kwargs={"idcollaborateur": kwargs["idcollaborateur"]})
