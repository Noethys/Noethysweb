# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import UniteConsentement, TypeConsentement
from parametrage.forms.unites_consentements import Formulaire
from django.db.models import Q, Count


class Page(crud.Page):
    model = UniteConsentement
    url_liste = "unites_consentements_liste"
    url_ajouter = "unites_consentements_ajouter"
    url_modifier = "unites_consentements_modifier"
    url_supprimer = "unites_consentements_supprimer"
    description_liste = "Voici ci-dessous la liste des unités de consentements. Il s'agit généralement des différentes version des documents (Exemple : Règlement intérieur de la structure)."
    description_saisie = "Saisissez toutes les informations concernant l'unité de consentement à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une unité de consentement"
    objet_pluriel = "des unités de consentements"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['categorie'] = self.Get_categorie()
        context['label_categorie'] = "Type de consentement"
        context['liste_categories'] = [(item.pk, item.nom) for item in TypeConsentement.objects.filter(Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)).order_by("nom")]
        if context['liste_categories']:
            # Si au moins un type de consentement existe
            context['boutons_liste'] = [
                {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'categorie': self.Get_categorie()}), "icone": "fa fa-plus"},
            ]
        else:
            # Si aucun type de consentement n'existe
            context['box_introduction'] = "Vous pouvez saisir ici des unités de consentement pour chaque type de consentement.<br><b>Vous devez avoir enregistré au moins un type de consentement avant de pouvoir ajouter des unités !</b>"
        return context

    def Get_categorie(self):
        type_consentement = self.kwargs.get('categorie', None)
        if type_consentement:
            return type_consentement
        type_consentement = TypeConsentement.objects.all().order_by("nom")
        return type_consentement[0].pk if type_consentement else 0

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idactivite au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["categorie"] = self.Get_categorie()
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'categorie': self.Get_categorie()})


class Liste(Page, crud.Liste):
    model = UniteConsentement
    template_name = "core/crud/liste_avec_categorie.html"

    def get_queryset(self):
        return UniteConsentement.objects.filter(Q(type_consentement=self.Get_categorie()) & self.Get_filtres("Q")).annotate(nbre_consentements=Count('consentement'))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ['idunite', 'nom', 'type_consentement__nom', 'date_debut', 'date_fin']
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        nbre_consentements = columns.TextColumn("Consentements associés", sources="nbre_consentements")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idunite_consentement', 'date_debut', 'date_fin', 'nbre_consentements']
            ordering = ['date_debut']
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut la catégorie dans les boutons d'actions """
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.type_consentement_id, instance.pk])),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.type_consentement_id, instance.pk])),
            ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    form_class = Formulaire
