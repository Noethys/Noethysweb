# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Famille, Quotient
from fiche_famille.forms.famille_quotients import Formulaire
from fiche_famille.views.famille import Onglet
from django.db.models import Q



class Page(Onglet):
    model = Quotient
    url_liste = "famille_quotients_liste"
    url_ajouter = "famille_quotients_ajouter"
    url_modifier = "famille_quotients_modifier"
    url_supprimer = "famille_quotients_supprimer"
    description_liste = "Saisissez ici les quotients familiaux de la famille."
    description_saisie = "Saisissez toutes les informations concernant le quotient et cliquez sur le bouton Enregistrer."
    objet_singulier = "un quotient familial"
    objet_pluriel = "des quotients familiaux"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        if not hasattr(self, "verbe_action"):
            context['box_titre'] = "Quotients familiaux"
        context['onglet_actif'] = "quotients"
        context['boutons_liste'] = [
            {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'idfamille': self.kwargs.get('idfamille', None)}), "icone": "fa fa-plus"},
        ]
        return context

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
    model = Quotient
    template_name = "fiche_famille/famille_liste.html"

    def get_queryset(self):
        return Quotient.objects.filter(Q(famille__pk=self.Get_idfamille()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ['idquotient', 'date_debut', 'date_fin', 'type_quotient__nom', 'quotient', 'revenu']

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        type_quotient = columns.TextColumn("Type de quotient", sources=["type_quotient__nom"])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idquotient', 'date_debut', 'date_fin', 'type_quotient', 'quotient', 'revenu']
            #hidden_columns = = ["idquotient"]
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ['date_debut']

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idindividu dans les boutons d'actions """
            view = kwargs["view"]
            # Récupération idindividu et idfamille
            kwargs = view.kwargs
            # Ajoute l'id de la ligne
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
