# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.db.models import Q
from core.views.mydatatableview import MyDatatable, columns, Deplacer_lignes
from core.views import crud
from core.models import CommandeModeleColonne, CommandeModele
from parametrage.forms.modeles_commandes_colonnes import Formulaire, LISTE_CHOIX_COLONNES


class Page(crud.Page):
    model = CommandeModeleColonne
    url_liste = "modeles_commandes_colonnes_liste"
    url_ajouter = "modeles_commandes_colonnes_ajouter"
    url_modifier = "modeles_commandes_colonnes_modifier"
    url_supprimer = "modeles_commandes_colonnes_supprimer"
    description_liste = "Voici la liste des colonnes du modèle de commande sélectionné ci-dessous."
    description_saisie = "Saisissez toutes les informations concernant la colonne à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une colonne"
    objet_pluriel = "des colonnes"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['categorie'] = self.Get_categorie()
        context['label_categorie'] = "Modèle"
        context['liste_categories'] = [(item.pk, item.nom) for item in CommandeModele.objects.filter(Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)).order_by("nom")]
        if context['liste_categories']:
            # Si au moins un type de cotisation existe
            context['boutons_liste'] = [
                {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'categorie': self.Get_categorie()}), "icone": "fa fa-plus"},
            ]
        else:
            # Si aucun type de cotisation n'existe
            context['box_introduction'] = "Vous pouvez saisir ici des colonnes pour chaque modèle de commande.<br><b>Vous devez avoir enregistré au moins un modèle avant de pouvoir ajouter des colonnes !</b>"
        return context

    def Get_categorie(self):
        modele = self.kwargs.get('categorie', None)
        if modele:
            return modele
        modele = CommandeModele.objects.all().order_by("nom")
        return modele[0].pk if modele else 0

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


class Deplacer(Deplacer_lignes):
    model = CommandeModeleColonne


class Liste(Page, crud.Liste):
    model = CommandeModeleColonne
    template_name = "core/crud/liste_avec_categorie.html"

    def get_queryset(self):
        return CommandeModeleColonne.objects.filter(Q(modele=self.Get_categorie()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        context['active_deplacements'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idcolonne", "nom", "modele__nom"]
        categorie = columns.TextColumn("Catégorie", sources=None, processor='Get_categorie')
        actions = columns.TextColumn("Actions", sources=None, processor="Get_actions_speciales")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idcolonne", "ordre", "nom", "categorie"]
            ordering = ["ordre"]

        def Get_categorie(self, instance, *args, **kwargs):
            for code, label in LISTE_CHOIX_COLONNES:
                if instance.categorie == code:
                    return label

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut la catégorie dans les boutons d'actions """
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.modele_id, instance.pk])),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.modele_id, instance.pk])),
            ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    pass
