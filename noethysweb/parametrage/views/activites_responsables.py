# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import ResponsableActivite, Activite
from parametrage.forms.activites_responsables import Formulaire
from parametrage.views.activites import Onglet
from django.db.models import Q


class Page(Onglet):
    model = ResponsableActivite
    url_liste = "activites_responsables_liste"
    url_ajouter = "activites_responsables_ajouter"
    url_modifier = "activites_responsables_modifier"
    url_supprimer = "activites_responsables_supprimer"
    description_liste = "Saisissez au moins un responsable d'activité. Celui-ci est utilisé en tant que signataire de certains documents édités par le logiciel."
    description_saisie = "Saisissez toutes les informations concernant le responsable à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un responsable de l'activité"
    objet_pluriel = "des responsables de l'activité"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Responsables d'activité"
        context['onglet_actif'] = "responsables"
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
    model = ResponsableActivite
    template_name = "parametrage/activite_liste.html"

    def get_queryset(self):
        return ResponsableActivite.objects.filter(Q(activite=self.Get_idactivite()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ['idresponsable', 'nom', 'fonction', 'defaut']

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        defaut = columns.TextColumn("Défaut", sources="defaut", processor='Get_default')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idresponsable', 'nom', 'fonction', 'defaut']
            ordering = ['nom']

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idactivite dans les boutons d'actions """
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.activite.idactivite, instance.pk])),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.activite.idactivite, instance.pk])),
            ]
            return self.Create_boutons_actions(html)

        def Get_default(self, instance, **kwargs):
            return "<i class='fa fa-check text-success'></i>" if instance.defaut else ""


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "parametrage/activite_edit.html"

    def form_valid(self, form):
        # Si le Défaut a été coché, on supprime le Défaut des autres objets
        if form.instance.defaut == True:
            self.model.objects.filter(activite=form.instance.activite).filter(defaut=True).update(defaut=False)
        return super().form_valid(form)


class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "parametrage/activite_edit.html"

    def form_valid(self, form):
        # Si le Défaut a été coché, on supprime le Défaut des autres objets
        if form.instance.defaut == True:
            self.model.objects.filter(activite=form.instance.activite).filter(defaut=True).update(defaut=False)
        return super().form_valid(form)


class Supprimer(Page, crud.Supprimer):
    template_name = "parametrage/activite_delete.html"

    # def delete(self, request, *args, **kwargs):
    #     reponse = super(Supprimer, self).delete(request, *args, **kwargs)
    #     if reponse.status_code != 303:
    #         # Si le défaut a été supprimé, on le réattribue à une autre objet
    #         if len(self.model.objects.filter(activite=self.object.activite).filter(defaut=True)) == 0:
    #             objet = self.model.objects.filter(activite=self.object.activite).first()
    #             if objet != None:
    #                 objet.defaut = True
    #                 objet.save()
    #     return reponse
