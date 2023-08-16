# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.db.models import Q
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import ContratCollaborateur
from collaborateurs.forms.collaborateur_contrats import Formulaire
from collaborateurs.views.collaborateur import Onglet


class Page(Onglet):
    model = ContratCollaborateur
    url_liste = "collaborateur_contrats_liste"
    url_ajouter = "collaborateur_contrats_ajouter"
    url_modifier = "collaborateur_contrats_modifier"
    url_supprimer = "collaborateur_contrats_supprimer"
    url_supprimer_plusieurs = "collaborateur_contrats_supprimer_plusieurs"
    description_liste = "Saisissez ici les contrats du collaborateur."
    description_saisie = "Saisissez toutes les informations concernant le contrat et cliquez sur le bouton Enregistrer."
    objet_singulier = "un contrat"
    objet_pluriel = "des contrats"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        if not hasattr(self, "verbe_action"):
            context['box_titre'] = "Contrats"
        context['onglet_actif'] = "contrats"
        context['boutons_liste'] = [
            {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'idcollaborateur': self.kwargs.get('idcollaborateur', None)}), "icone": "fa fa-plus"},
        ]
        return context

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idcollaborateur"] = self.Get_idcollaborateur()
        return form_kwargs

    def get_success_url(self):
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idcollaborateur': self.kwargs.get('idcollaborateur', None)})


class Liste(Page, crud.Liste):
    model = ContratCollaborateur
    template_name = "collaborateurs/collaborateur_liste.html"

    def get_queryset(self):
        return ContratCollaborateur.objects.select_related("type_poste").filter(Q(collaborateur_id=self.Get_idcollaborateur()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ["idcontrat", "date_debut", "date_fin"]
        nom_type_poste = columns.TextColumn("Poste", sources=["type_poste__nom"], processor='Get_nom_type_poste')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idcontrat", "date_debut", "date_fin", "nom_type_poste", "actions"]
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ['date_debut']

        def Get_nom_type_poste(self, instance, *args, **kwargs):
            return instance.type_poste.nom

        def Get_actions_speciales(self, instance, *args, **kwargs):
            view = kwargs["view"]
            kwargs = view.kwargs
            kwargs["pk"] = instance.pk
            html = [
                self.Create_bouton_modifier(url=reverse(view.url_modifier, kwargs=kwargs)),
                self.Create_bouton_supprimer(url=reverse(view.url_supprimer, kwargs=kwargs)),
                self.Create_bouton_word(url=reverse("collaborateur_voir_contrat", kwargs={"idcollaborateur": kwargs["idcollaborateur"], "idcontrat": instance.pk})), ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "collaborateurs/collaborateur_edit.html"


class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "collaborateurs/collaborateur_edit.html"


class Supprimer(Page, crud.Supprimer):
    template_name = "collaborateurs/collaborateur_delete.html"
