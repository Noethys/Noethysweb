# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import UniteCotisation, TypeCotisation
from core.utils import utils_texte
from parametrage.forms.unites_cotisations import Formulaire


class Page(crud.Page):
    model = UniteCotisation
    url_liste = "unites_cotisations_liste"
    url_ajouter = "unites_cotisations_ajouter"
    url_modifier = "unites_cotisations_modifier"
    url_supprimer = "unites_cotisations_supprimer"
    description_liste = "Voici ci-dessous la liste des unités d'adhésions."
    description_saisie = "Saisissez toutes les informations concernant l'unité d'adhésion à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une unité d'adhésion"
    objet_pluriel = "des unités d'adhésions"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['categorie'] = self.Get_categorie()
        context['label_categorie'] = "Type d'adhésion"
        context['liste_categories'] = [(item.pk, item.nom) for item in TypeCotisation.objects.filter(Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)).order_by("nom")]
        if context['liste_categories']:
            # Si au moins un type de cotisation existe
            context['boutons_liste'] = [
                {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'categorie': self.Get_categorie()}), "icone": "fa fa-plus"},
            ]
        else:
            # Si aucun type de cotisation n'existe
            context['box_introduction'] = "Vous pouvez saisir ici des unités d'adhésion pour chaque type d'adhésion.<br><b>Vous devez avoir enregistré au moins un type d'adhésion avant de pouvoir ajouter des unités !</b>"
        return context

    def Get_categorie(self):
        type_cotisation = self.kwargs.get('categorie', None)
        if type_cotisation:
            return type_cotisation
        type_cotisation = TypeCotisation.objects.all().order_by("nom")
        return type_cotisation[0].pk if type_cotisation else 0

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
    model = UniteCotisation
    template_name = "core/crud/liste_avec_categorie.html"

    def get_queryset(self):
        return UniteCotisation.objects.filter(Q(type_cotisation=self.Get_categorie()) & self.Get_filtres("Q")).annotate(nbre_cotisations=Count("cotisation"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ['idunite', 'nom', 'type_cotisation__nom', 'montant', 'defaut']
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        duree_validite = columns.DisplayColumn("Validité", sources="duree_validite", processor='Get_validite')
        type_cotisation = columns.TextColumn("Type d'adhésion", sources=["type_cotisation__nom"])
        defaut = columns.TextColumn("Défaut", sources="defaut", processor='Get_default')
        montant = columns.TextColumn("Tarif", sources="tarif", processor='Get_montant')
        nbre_cotisations = columns.TextColumn("Adhésions associées", sources="nbre_cotisations")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idunite_cotisation', 'nom', 'type_cotisation', 'duree_validite', 'montant', 'defaut', 'nbre_cotisations']
            ordering = ['nom']

        def Get_validite(self, instance, **kwargs):
            if instance.duree!= None:
                liste_duree = []
                try:
                    jours, mois, annees = instance.duree.split("-")
                    jours, mois, annees = int(jours[1:]), int(mois[1:]), int(annees[1:])
                    if annees > 0: liste_duree.append("%d années" % annees)
                    if mois > 0: liste_duree.append("%d mois" % mois)
                    if jours > 0: liste_duree.append("%d jours" % jours)
                except:
                    pass
                return ", ".join(liste_duree)
            else:
                periode = "Du %s au %s" % (instance.date_debut.strftime('%d/%m/%Y'), instance.date_fin.strftime('%d/%m/%Y'))
                return periode

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut la catégorie dans les boutons d'actions """
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.type_cotisation_id, instance.pk])),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.type_cotisation_id, instance.pk])),
            ]
            return self.Create_boutons_actions(html)

        def Get_default(self, instance, **kwargs):
            return "<i class='fa fa-check text-success'></i>" if instance.defaut else ""

        def Get_montant(self, instance, **kwargs):
            if instance.tarifs:
                return "Selon le QF"
            elif not instance.montant:
                return "Gratuit"
            else:
                return utils_texte.Formate_montant(instance.montant)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

    def form_valid(self, form):
        # Si le Défaut a été coché, on supprime le Défaut des autres unités
        if form.instance.defaut:
            self.model.objects.filter(type_cotisation=form.instance.type_cotisation).filter(defaut=True).update(defaut=False)
        return super().form_valid(form)


class Modifier(Page, crud.Modifier):
    form_class = Formulaire

    def form_valid(self, form):
        # Si le Défaut a été coché, on supprime le Défaut des autres unités
        if form.instance.defaut:
            self.model.objects.filter(type_cotisation=form.instance.type_cotisation).filter(defaut=True).update(defaut=False)
        return super().form_valid(form)


class Supprimer(Page, crud.Supprimer):
    form_class = Formulaire

    def delete(self, request, *args, **kwargs):
        reponse = super(Supprimer, self).delete(request, *args, **kwargs)
        if reponse.status_code != 303:
            # Si le défaut a été supprimé, on le réattribue à un autre modèle
            if len(self.model.objects.filter(type_cotisation=kwargs.get("categorie")).filter(defaut=True)) == 0:
                objet = self.model.objects.filter(type_cotisation=kwargs.get("categorie")).first()
                if objet:
                    objet.defaut = True
                    objet.save()
        return reponse
