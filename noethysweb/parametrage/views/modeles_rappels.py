# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import ModeleRappel
from parametrage.forms.modeles_rappels import Formulaire
from copy import deepcopy


class Page(crud.Page):
    model = ModeleRappel
    url_liste = "modeles_rappels_liste"
    url_ajouter = "modeles_rappels_ajouter"
    url_modifier = "modeles_rappels_modifier"
    url_supprimer = "modeles_rappels_supprimer"
    url_dupliquer = "modeles_rappels_dupliquer"
    description_liste = "Les modèles de lettres de rappel contiennent les textes des relances adressées aux familles qui ont des factures impayées. Le modèle proposé dépend du nombre de jours de retard : créez par exemple un premier rappel, puis une relance plus ferme."
    description_saisie = "Saisissez le nom du modèle, la tranche de jours de retard concernée, le titre et le texte de la lettre, puis cliquez sur le bouton Enregistrer."
    objet_singulier = "un modèle de lettre de rappel"
    objet_pluriel = "des modèles de lettres de rappel"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]



class Liste(Page, crud.Liste):
    model = ModeleRappel

    def get_queryset(self):
        return ModeleRappel.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ['idtexte', 'label']
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idtexte', 'label', 'retard_min', 'retard_max']
            ordering = ['label']

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut la duplication dans les boutons d'actions """
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
    pass

class Dupliquer(Page, crud.Dupliquer):

    def post(self, request, **kwargs):
        # Récupération du modèle à dupliquer
        modele = self.model.objects.get(pk=kwargs.get("pk", None))

        # Duplication du modèle
        nouveau_modele = deepcopy(modele)
        nouveau_modele.pk = None
        nouveau_modele.label = "Copie de %s" % modele.label
        nouveau_modele.save()

        # Redirection vers l'objet dupliqué
        if "dupliquer_ouvrir" in request.POST:
            url = reverse(self.url_modifier, args=[nouveau_modele.pk])
        else:
            url = None

        return self.Redirection(url=url)
