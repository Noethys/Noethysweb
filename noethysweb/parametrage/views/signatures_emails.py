# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import SignatureEmail
from parametrage.forms.signatures_emails import Formulaire
from copy import deepcopy


class Page(crud.Page):
    model = SignatureEmail
    url_liste = "signatures_emails_liste"
    url_ajouter = "signatures_emails_ajouter"
    url_modifier = "signatures_emails_modifier"
    url_supprimer = "signatures_emails_supprimer"
    url_dupliquer = "signatures_emails_dupliquer"
    description_liste = "Voici la liste des signatures d'emails que vous pouvez intégrer dans les emails."
    description_saisie = "Saisissez toutes les informations concernant la signature à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une signature d'email"
    objet_pluriel = "des signatures d'emails"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = SignatureEmail

    def get_queryset(self):
        return SignatureEmail.objects.filter(self.Get_filtres("Q"), self.Get_condition_structure())

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idsignature", 'nom']
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idsignature", 'nom']
            ordering = ['nom']

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.pk])),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.pk])),
                self.Create_bouton_dupliquer(url=reverse(kwargs["view"].url_dupliquer, args=[instance.pk])),
            ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire


class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    form_class = Formulaire


class Dupliquer(Page, crud.Dupliquer):
    def post(self, request, **kwargs):
        # Récupération de la signature à dupliquer
        signature = self.model.objects.get(pk=kwargs.get("pk", None))

        # Duplication
        nouvelle_signature = deepcopy(signature)
        nouvelle_signature.pk = None
        nouvelle_signature.nom = "Copie de %s" % signature.nom
        nouvelle_signature.save()

        # Redirection vers l'objet dupliqué
        if "dupliquer_ouvrir" in request.POST:
            url = reverse(self.url_modifier, args=[nouvelle_signature.pk,])
        else:
            url = None

        return self.Redirection(url=url)
