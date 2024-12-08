# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers, Deplacer_lignes
from core.views import crud
from parametrage.views.activites import Onglet
from core.models import Unite, Activite
from parametrage.forms.activites_unites_conso import Formulaire
from django.db.models import Q


class Page(Onglet):
    model = Unite
    url_liste = "activites_unites_conso_liste"
    url_ajouter = "activites_unites_conso_ajouter"
    url_modifier = "activites_unites_conso_modifier"
    url_supprimer = "activites_unites_conso_supprimer"
    description_liste = "Vous pouvez saisir ici des unités de consommation de l'activité. Exemples : Journée, Matin, Repas, Séance, Atelier... Elles sont utilisées principalement si vous souhaitez enregistrer des réservations ou des présences."
    description_saisie = "Saisissez toutes les informations concernant l'unité de consommation à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une unité de consommation"
    objet_pluriel = "des unités de consommation"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Unités de consommation"
        context['onglet_actif'] = "unites_conso"
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



class Deplacer(Deplacer_lignes):
    model = Unite


class Liste(Page, crud.Liste):
    model = Unite
    template_name = "parametrage/activite_liste.html"

    def get_queryset(self):
        return Unite.objects.filter(Q(activite=self.Get_idactivite()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['active_deplacements'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ['idunite', 'nom', 'abrege', 'type']

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idunite', 'ordre', 'nom', 'abrege', 'type']
            ordering = ['ordre']

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
    manytomany_associes = [
        ("unité(s) de remplissage", "unite_remplissage_unites"),
        ("combinaison(s) de tarif", "combi_tarif_unites")
    ]

    # def delete(self, request, *args, **kwargs):
    #     reponse = super(Supprimer, self).delete(request, *args, **kwargs)
    #     if reponse.status_code != 303:
    #         liste_objects = self.model.objects.filter(activite=self.object.activite).order_by("ordre")
    #         ordre = 1
    #         for objet in liste_objects:
    #             if objet.ordre != ordre:
    #                 objet.ordre = ordre
    #                 objet.save()
    #             ordre += 1
    #     return reponse
