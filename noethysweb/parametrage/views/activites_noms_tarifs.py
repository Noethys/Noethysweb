# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers, Deplacer_lignes
from core.views import crud
from parametrage.views.activites import Onglet
from core.models import NomTarif, Activite
from parametrage.forms.activites_noms_tarifs import Formulaire
from django.db.models import Q


class Page(Onglet):
    model = NomTarif
    url_liste = "activites_noms_tarifs_liste"
    url_ajouter = "activites_noms_tarifs_ajouter"
    url_modifier = "activites_noms_tarifs_modifier"
    url_supprimer = "activites_noms_tarifs_supprimer"
    description_liste = "Vous pouvez saisir ici un nom de tarif pour l'activité. Exemples : Journée avec repas, Repas, Matin, Atelier, Séjour à la neige - Février 2026, Yoga - Saison 2024-25... Vous devez obligatoirement créer au moins un nom de tarif avant de créer des tarifs."
    description_saisie = "Saisissez toutes les informations concernant le nom de tarif à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un nom de tarif"
    objet_pluriel = "des noms de tarifs"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Noms de tarifs"
        context['onglet_actif'] = "noms_tarifs"
        context['boutons_liste'] = [
            {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'idactivite': self.Get_idactivite()}), "icone": "fa fa-plus"},
        ]
        return context

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idactivite au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idactivite"] = self.Get_idactivite()
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idactivite': self.Get_idactivite()})



class Liste(Page, crud.Liste):
    model = NomTarif
    template_name = "parametrage/activite_liste.html"

    def get_queryset(self):
        return NomTarif.objects.filter(Q(activite=self.Get_idactivite()) & self.Get_filtres("Q"))

    class datatable_class(MyDatatable):
        filtres = ['idnom_tarif', 'nom']

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idnom_tarif', 'nom']
            ordering = ['nom']

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idactivite dans les boutons d'actions """
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.activite.idactivite, instance.pk])),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.activite.idactivite, instance.pk])),
            ]
            return self.Create_boutons_actions(html)



class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "parametrage/activite_edit.html"

class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "parametrage/activite_edit.html"

class Supprimer(Page, crud.Supprimer):
    template_name = "parametrage/activite_delete.html"
