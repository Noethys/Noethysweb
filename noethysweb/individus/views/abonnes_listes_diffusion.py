# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.http import HttpResponseRedirect
from django.urls import reverse_lazy, reverse
from django.db.models import Q
from django.contrib import messages
from core.views.mydatatableview import MyDatatable, columns
from core.views import crud
from core.models import Individu, ListeDiffusion
from parametrage.forms.modeles_word import Formulaire


class Page(crud.Page):
    model = Individu
    url_liste = "abonnes_listes_diffusion_liste"
    url_ajouter = "abonnes_listes_diffusion_ajouter"
    url_supprimer = "abonnes_listes_diffusion_supprimer"
    url_supprimer_plusieurs = "abonnes_listes_diffusion_supprimer_plusieurs"
    description_liste = "Sélectionnez une liste de diffusion dans la liste et consultez les abonnés correspondants. Cliquez sur Ajouter pour abonner un ou plusieurs individus."
    description_saisie = "Cochez les individus à ajouter et cliquez sur le bouton Enregistrer."
    objet_singulier = "un abonné à une liste de diffusion"
    objet_pluriel = "des abonnés à des listes de diffusion"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['categorie'] = self.Get_categorie()
        context['label_categorie'] = "Liste de diffusion"
        context['categorie'] = int(self.Get_categorie()) if self.Get_categorie() else None
        context['liste_categories'] = [(item.pk, item.nom) for item in ListeDiffusion.objects.all().order_by("nom")]
        if context['categorie']:
            context['boutons_liste'] = [{"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'idliste_diffusion': self.Get_categorie()}), "icone": "fa fa-plus"},]
        context['url_supprimer_plusieurs'] = reverse_lazy(self.url_supprimer_plusieurs, kwargs={"idliste_diffusion": self.Get_categorie(), "listepk": "xxx"})
        return context

    def Get_categorie(self):
        idcategorie = self.kwargs.get('categorie', None)
        if idcategorie:
            return idcategorie
        liste = ListeDiffusion.objects.order_by("nom").first()
        return liste.pk if liste else 0

    def get_form_kwargs(self, **kwargs):
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
    model = Individu
    template_name = "core/crud/liste_avec_categorie.html"

    def get_queryset(self):
        liste_diff = ListeDiffusion.objects.get(pk=self.Get_categorie()) if self.Get_categorie() else 0
        return Individu.objects.filter(Q(listes_diffusion=liste_diff) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        context['active_checkbox'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["igenerique:pk",]
        check = columns.CheckBoxSelectColumn(label="")
        rue_resid = columns.TextColumn("Rue", processor='Get_rue_resid')
        cp_resid = columns.TextColumn("CP", processor='Get_cp_resid')
        ville_resid = columns.TextColumn("Ville",  sources=None, processor='Get_ville_resid')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', "idindividu", "nom", "prenom", "rue_resid", "cp_resid", "ville_resid", "actions"]
            ordering = ["nom", "prenom"]

        def Get_rue_resid(self, instance, *args, **kwargs):
            return instance.rue_resid

        def Get_cp_resid(self, instance, *args, **kwargs):
            return instance.cp_resid

        def Get_ville_resid(self, instance, *args, **kwargs):
            return instance.ville_resid

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut la catégorie dans les boutons d'actions """
            html = [
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[kwargs["view"].Get_categorie(), instance.pk])),
            ]
            return self.Create_boutons_actions(html)


class Supprimer(Page, crud.Supprimer):
    form_class = Formulaire
    check_protections = False

    def get_context_data(self, **kwargs):
        """ Ajouté pour contourner la protection anti-suppression de l'individu """
        context = super(Supprimer, self).get_context_data(**kwargs)
        return context

    def delete(self, request, *args, **kwargs):
        # Suppression de l'abonnement
        liste_diffusion = ListeDiffusion.objects.get(pk=int(kwargs["categorie"]))
        individu = Individu.objects.get(pk=int(kwargs["pk"]))
        individu.listes_diffusion.remove(liste_diffusion)

        # Confirmation de la suppression
        messages.add_message(self.request, messages.SUCCESS, "Suppression de l'abonnement effectuée avec succès")
        return HttpResponseRedirect(reverse_lazy(self.url_liste, kwargs={'categorie': kwargs["categorie"]}))


class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
    check_protections = False

    def get_context_data(self, **kwargs):
        """ Ajouté pour contourner la protection anti-suppression de l'individu """
        context = super(Supprimer_plusieurs, self).get_context_data(**kwargs)
        return context

    def post(self, request, **kwargs):
        # Suppression des abonnements
        liste_diffusion = ListeDiffusion.objects.get(pk=int(kwargs["idliste_diffusion"]))
        for individu in self.get_objets():
            individu.listes_diffusion.remove(liste_diffusion)

        # Confirmation de la suppression
        messages.add_message(self.request, messages.SUCCESS, "Suppression des abonnements effectuée avec succès")
        return HttpResponseRedirect(reverse_lazy(self.url_liste, kwargs={'categorie': kwargs["idliste_diffusion"]}))
