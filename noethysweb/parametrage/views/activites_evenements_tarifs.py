# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers, Deplacer_lignes
from core.views import crud
from core.utils import utils_dates
from parametrage.views.activites import Onglet
from parametrage.views import activites_tarifs
from core.models import Tarif, Activite, TarifLigne, CombiTarif, NomTarif, LISTE_METHODES_TARIFS, DICT_COLONNES_TARIFS, Evenement
from parametrage.forms.activites_tarifs import Formulaire
from django.db.models import Q


class Page(Onglet):
    model = Tarif
    url_liste = "activites_evenements_tarifs_liste"
    url_ajouter = "activites_evenements_tarifs_ajouter"
    url_modifier = "activites_evenements_tarifs_modifier"
    url_supprimer = "activites_evenements_tarifs_supprimer"
    url_dupliquer = "activites_evenements_tarifs_dupliquer"
    description_liste = "Vous pouvez saisir ici des tarifs avancés pour l'événement."
    description_saisie = "Saisissez toutes les informations concernant le tarif et cliquez sur le bouton Enregistrer."
    objet_singulier = "un tarif d'événement"
    objet_pluriel = "des tarifs d'événement"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        evenement = Evenement.objects.get(pk=self.Get_evenement())
        context['box_titre'] = "Tarifs avancés de l'événement %s du %s" % (evenement.nom, utils_dates.ConvertDateToFR(evenement.date))
        context['onglet_actif'] = "evenements"
        context['liste_methodes_tarifs'] = LISTE_METHODES_TARIFS
        context['dict_colonnes_tarifs'] = DICT_COLONNES_TARIFS
        context['url_liste'] = self.url_liste
        context['idactivite'] = self.Get_idactivite()
        context['boutons_liste'] = [
            {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'idactivite': self.Get_idactivite(), 'evenement': self.Get_evenement()}), "icone": "fa fa-plus"},
            {"label": "Retour à la liste des événements", "classe": "btn btn-default", "href": reverse_lazy("activites_evenements_liste", kwargs={'idactivite': self.Get_idactivite()}), "icone": "fa fa-arrow-circle-o-left"},
        ]
        return context

    def Get_evenement(self):
        return self.kwargs.get('evenement', None)

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idactivite au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idactivite"] = self.Get_idactivite()
        form_kwargs["evenement"] = self.Get_evenement()
        form_kwargs["methode"] = self.request.POST.get("methode")
        form_kwargs["tarifs_lignes_data"] = self.request.POST.get("tarifs_lignes_data")
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idactivite': self.Get_idactivite(), 'evenement': self.Get_evenement()})



class Liste(Page, crud.Liste):
    model = Tarif
    template_name = "parametrage/activite_liste.html"

    def get_queryset(self):
        return Tarif.objects.prefetch_related("categories_tarifs").filter(Q(activite=self.Get_idactivite()) & Q(evenement=self.Get_evenement()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        return context

    class datatable_class(MyDatatable):
        filtres = ['idtarif', 'description', 'methode']

        categories = columns.TextColumn("Catégories", sources=None, processor='Get_categories')
        methode = columns.TextColumn("Méthode", sources=["methode"], processor='Get_methode')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idtarif', 'description', 'categories', 'methode']

        def Get_methode(self, instance, *args, **kwargs):
            return instance.get_methode_display()

        def Get_categories(self, instance, *args, **kwargs):
            return ", ".join([categorie.nom for categorie in instance.categories_tarifs.all()])

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idactivite dans les boutons d'actions """
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.activite.idactivite, instance.evenement_id, instance.pk])),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.activite.idactivite, instance.evenement_id, instance.pk])),
                self.Create_bouton_dupliquer(url=reverse(kwargs["view"].url_dupliquer, args=[instance.activite.idactivite, instance.evenement_id, instance.pk])),
            ]
            return self.Create_boutons_actions(html)


class ClasseCommune(Page, activites_tarifs.ClasseCommune):
    form_class = Formulaire


class Ajouter(ClasseCommune, crud.Ajouter):
    form_class = Formulaire
    template_name = "parametrage/activite_edit.html"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Ajouter, self).get_context_data(**kwargs)
        evenement = Evenement.objects.get(pk=self.Get_evenement())
        context['box_titre'] = "Tarif avancé pour l'événement %s du %s" % (evenement.nom, utils_dates.ConvertDateToFR(evenement.date))
        return context


class Modifier(ClasseCommune, crud.Modifier):
    form_class = Formulaire
    template_name = "parametrage/activite_edit.html"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Modifier, self).get_context_data(**kwargs)
        evenement = Evenement.objects.get(pk=self.Get_evenement())
        context['box_titre'] = "Tarif avancé pour l'événement %s du %s" % (evenement.nom, utils_dates.ConvertDateToFR(evenement.date))
        return context

class Supprimer(Page, activites_tarifs.Supprimer):
    template_name = "parametrage/activite_delete.html"

class Dupliquer(Page, activites_tarifs.Dupliquer):
    template_name = "parametrage/activite_dupliquer.html"
