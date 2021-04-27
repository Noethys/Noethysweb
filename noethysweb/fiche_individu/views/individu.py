# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Individu, Famille, Message, Rattachement
from django.views.generic.detail import DetailView
from fiche_individu.forms.individu import Formulaire
from core.views.base import CustomView
from django.db.models import Q
from fiche_individu.utils.utils_individu import LISTE_ONGLETS


class Page(crud.Page):
    model = Individu
    url_liste = "individu_liste"
    url_ajouter = "individu_ajouter"
    url_modifier = "individu_resume"
    url_supprimer = "individu_supprimer"
    description_liste = "Voici ci-dessous la liste des individus."
    description_saisie = "Saisissez ou sélectionnez le premier représentant de la famille à créer. Saisissez toutes les informations concernant l'individu à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un individu"
    objet_pluriel = "des individus"
    # boutons_liste = [
    #     {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    # ]


class Liste(Page, crud.Liste):
    model = Rattachement

    def get_queryset(self):
        return Rattachement.objects.select_related('individu', 'famille').filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ['idrattachement', 'individu__pk', "individu__nom", "individu__prenom", "famille__nom", "individu__date_naiss", "individu__rue_resid", "individu__cp_resid", "individu__ville_resid"]
        idindividu = columns.IntegerColumn("ID", sources=['individu__pk'])
        nom = columns.TextColumn("Nom", sources=['individu__nom'])
        prenom = columns.TextColumn("Prénom", sources=['individu__prenom'])
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        profil = columns.TextColumn("Profil", processor='Get_profil')
        date_naiss = columns.TextColumn("Date naiss.", sources=['individu__date_naiss'], processor=helpers.format_date('%d/%m/%Y'))
        rue_resid = columns.TextColumn("Rue", sources=['individu__rue_resid'])
        cp_resid = columns.TextColumn("CP", sources=['individu__cp_resid'])
        ville_resid = columns.TextColumn("Ville", sources=['individu__ville_resid'])
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idrattachement', 'idindividu', "nom", "prenom", "profil", "famille", "date_naiss", "rue_resid", "cp_resid", "ville_resid"]
            hidden_columns = ["idrattachement"]
            ordering = ["nom", "prenom"]

        def Get_profil(self, instance, **kwargs):
            if instance.categorie == 1: return "Responsable" + " titulaire" if instance.titulaire else ""
            if instance.categorie == 2: return "Enfant"
            if instance.categorie == 3: return "Contact"
            return ""

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton(url=reverse("individu_resume", args=[instance.famille_id, instance.individu_id]), title="Ouvrir la fiche individuelle", icone="fa-user"),
                self.Create_bouton(url=reverse("famille_resume", args=[instance.famille_id]), title="Ouvrir la fiche famille", icone="fa-users"),
                self.Create_bouton(url=reverse("famille_consommations", args=[instance.famille_id, instance.individu_id]), title="Ouvrir la grille des consommations", icone="fa-calendar"),
            ]
            return self.Create_boutons_actions(html)



# class Supprimer(Page, crud.Supprimer):
#     form_class = Formulaire
#
#     def get_object(self):
#         return Individu.objects.get(pk=self.kwargs['idindividu'])




class Onglet(CustomView):
    menu_code = "individus_toc"
    liste_onglets = LISTE_ONGLETS

    def get_context_data(self, **kwargs):
        context = super(Onglet, self).get_context_data(**kwargs)
        context['page_titre'] = "Fiche individuelle"
        context['liste_onglets'] = [dict_onglet for dict_onglet in self.liste_onglets if self.request.user.has_perm("core.individu_%s" % dict_onglet["code"])]
        context['idindividu'] = self.kwargs['idindividu']
        context['individu'] = Individu.objects.get(pk=self.kwargs['idindividu'])
        if self.kwargs.get('idfamille', None):
            context['idfamille'] = self.kwargs['idfamille']
            context['famille'] = Famille.objects.get(pk=self.kwargs['idfamille'])
        else:
            context['idfamille'] = None
            context['famille'] = None
        return context

    def Get_idindividu(self):
        return self.kwargs.get('idindividu', None)

    def Get_idfamille(self):
        return self.kwargs.get('idfamille', None)

    def Maj_infos_famille(self):
        """ Met à jour les infos de toutes les familles rattachées à cet individu"""
        self.object.Maj_infos()

        # Met à jour en cascade les adresses rattachées à cet individu
        for individu in Individu.objects.filter(adresse_auto=self.Get_idindividu()):
            individu.Maj_infos()

        # Met à jour le nom des titulaires de la famille et l'adresse familiale
        rattachements = Rattachement.objects.select_related('famille').filter(individu_id=self.Get_idindividu())
        for rattachement in rattachements:
            rattachement.famille.Maj_infos()


class Resume(Onglet, DetailView):
    template_name = "fiche_individu/individu_resume.html"

    def get_context_data(self, **kwargs):
        context = super(Resume, self).get_context_data(**kwargs)
        context['box_titre'] = self.object.nom
        context['box_introduction'] = ""
        context['onglet_actif'] = "resume"
        context['messages_individu'] = Message.objects.filter(individu_id=self.kwargs['idindividu']).order_by("date_saisie")
        return context

    def get_object(self):
        return Individu.objects.get(pk=self.kwargs['idindividu'])


