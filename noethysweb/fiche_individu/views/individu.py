# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.urls import reverse
from django.db.models import Q
from django.views.generic.detail import DetailView
from core.views.mydatatableview import MyDatatable, columns
from core.views import crud
from core.views.base import CustomView
from core.models import Individu, Famille, Note, Rattachement, Inscription
from core.utils import utils_texte, utils_dates
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


class Liste(Page, crud.Liste):
    model = Rattachement

    def get_queryset(self):
        try:
            return Rattachement.objects.select_related('individu', 'famille').filter(self.Get_filtres("Q"))
        except:
            return Rattachement.objects.select_related('individu', 'famille').all()

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ['idrattachement', "ipresent:individu", "fpresent:famille", "iscolarise:individu", "fscolarise:famille", "datenaiss:individu",
                   'individu__pk', "individu__nom", "individu__prenom", "famille__nom", "individu__rue_resid",
                   "individu__tel_domicile", "individu__tel_mobile", "individu__mail", "individu__cp_resid", "individu__ville_resid", "genre"]
        idindividu = columns.IntegerColumn("ID", sources=['individu__pk'])
        nom = columns.TextColumn("Nom", sources=['individu__nom'])
        prenom = columns.TextColumn("Prénom", sources=['individu__prenom'])
        genre = columns.TextColumn("Genre", sources=None, processor='Get_genre')
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        profil = columns.TextColumn("Profil", sources=['Get_profil'])
        tel_domicile = columns.TextColumn("Tél domicile", processor="Get_tel_domicile")
        tel_mobile = columns.TextColumn("Tél portable", processor="Get_tel_mobile")
        secteur = columns.TextColumn("Secteur", processor="Get_secteur")
        mail = columns.TextColumn("Email", processor="Get_mail")
        date_naiss = columns.TextColumn("Date naiss.", processor="Get_date_naiss")
        age = columns.TextColumn("Age", sources=['Get_age'], processor="Get_age")
        rue_resid = columns.TextColumn("Rue", processor='Get_rue_resid')
        cp_resid = columns.TextColumn("CP", processor='Get_cp_resid')
        ville_resid = columns.TextColumn("Ville",  sources=None, processor='Get_ville_resid')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idrattachement', 'idindividu', "nom", "prenom", "profil", "famille", "age", "date_naiss", "genre", "rue_resid", "cp_resid", "ville_resid", "tel_domicile", "tel_mobile", "mail", "secteur"]
            hidden_columns = ["idrattachement", "tel_domicile", "tel_mobile", "mail", "genre", "secteur"]
            ordering = ["nom", "prenom"]

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton(url=reverse("individu_resume", args=[instance.famille_id, instance.individu_id]), title="Ouvrir la fiche individuelle", icone="fa-user"),
                self.Create_bouton(url=reverse("famille_resume", args=[instance.famille_id]), title="Ouvrir la fiche famille", icone="fa-users"),
                self.Create_bouton(url=reverse("famille_consommations", args=[instance.famille_id, instance.individu_id]), title="Ouvrir la grille des consommations", icone="fa-calendar"),
            ]
            return self.Create_boutons_actions(html)

        def Get_tel_domicile(self, instance, *args, **kwargs):
            return instance.individu.tel_domicile

        def Get_tel_mobile(self, instance, *args, **kwargs):
            return instance.individu.tel_mobile

        def Get_mail(self, instance, *args, **kwargs):
            return instance.individu.mail

        def Get_age(self, instance, *args, **kwargs):
            return instance.individu.Get_age()

        def Get_date_naiss(self, instance, *args, **kwargs):
            return utils_dates.ConvertDateToFR(instance.individu.date_naiss)

        def Get_rue_resid(self, instance, *args, **kwargs):
            return instance.individu.rue_resid

        def Get_cp_resid(self, instance, *args, **kwargs):
            return instance.individu.cp_resid

        def Get_ville_resid(self, instance, *args, **kwargs):
            return instance.individu.ville_resid

        def Get_secteur(self, instance, *args, **kwargs):
            return instance.individu.secteur

        def Get_genre(self, instance, *args, **kwargs):
            return instance.individu.Get_sexe()


class Onglet(CustomView):
    menu_code = "individus_toc"
    objet_singulier = "un individu"
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

        # Notes de l'individu
        conditions = (Q(utilisateur=self.request.user) | Q(utilisateur__isnull=True)) & (Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True))
        context['notes'] = Note.objects.filter(conditions, individu_id=self.kwargs['idindividu']).order_by("date_saisie")

        # Activités actuelles
        conditions = Q(individu_id=self.Get_idindividu()) & Q(date_debut__lte=datetime.date.today()) & (Q(date_fin__isnull=True) | Q(date_fin__gte=datetime.date.today()))
        conditions &= (Q(activite__date_fin__isnull=True) | Q(activite__date_fin__gte=datetime.date.today()))
        liste_activites = {inscription.activite.nom: True for inscription in Inscription.objects.select_related("activite").filter(conditions).order_by("date_debut")}
        context['inscriptions'] = utils_texte.Convert_liste_to_texte_virgules(list(liste_activites.keys()))

        return context

    def get_object(self):
        return Individu.objects.get(pk=self.kwargs['idindividu'])
