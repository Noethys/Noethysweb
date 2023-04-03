# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.db.models import Q
from django.views.generic.detail import DetailView
from django.contrib import messages
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.views.base import CustomView
from core.models import Collaborateur, Note
from collaborateurs.forms.collaborateur import Formulaire
from collaborateurs.utils.utils_collaborateur import LISTE_ONGLETS
from collaborateurs.utils import utils_pieces_manquantes


class Page(crud.Page):
    model = Collaborateur
    url_liste = "collaborateur_liste"
    url_ajouter = "collaborateur_ajouter"
    url_modifier = "collaborateur_resume"
    url_supprimer = "collaborateur_supprimer"
    description_liste = "Voici ci-dessous la liste des collaborateurs."
    description_saisie = "Saisissez toutes les informations concernant le collaborateur à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un collaborateur"
    objet_pluriel = "des collaborateurs"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = Collaborateur

    def get_queryset(self):
        conditions = (Q(groupes__superviseurs=self.request.user) | Q(groupes__superviseurs__isnull=True))
        try:
            return Collaborateur.objects.filter(conditions, self.Get_filtres("Q"))
        except:
            return Collaborateur.objects.filter(conditions)

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ["idcollaborateur", "nom", "prenom"]
        rue_resid = columns.TextColumn("Rue", processor='Get_rue_resid')
        cp_resid = columns.TextColumn("CP", processor='Get_cp_resid')
        ville_resid = columns.TextColumn("Ville",  sources=None, processor='Get_ville_resid')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idcollaborateur", "nom", "prenom", "rue_resid", "cp_resid", "ville_resid"]
            ordering = ["nom", "prenom"]

        def Get_rue_resid(self, instance, *args, **kwargs):
            return instance.rue_resid

        def Get_cp_resid(self, instance, *args, **kwargs):
            return instance.cp_resid

        def Get_ville_resid(self, instance, *args, **kwargs):
            return instance.ville_resid

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_modifier(url=reverse("collaborateur_resume", args=[instance.pk])),
                self.Create_bouton_supprimer(url=reverse("collaborateur_supprimer", args=[instance.pk])),
                # self.Create_bouton(url=reverse("famille_consommations", args=[instance.famille_id, instance.collaborateur_id]), title="Ouvrir la grille des consommations", icone="fa-calendar"),
            ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

    def get_success_url(self):
        """ Renvoie vers la page résumé du collaborateur """
        messages.add_message(self.request, messages.SUCCESS, "Ajout enregistré")
        return reverse_lazy("collaborateur_resume", kwargs={'idcollaborateur': self.object.idcollaborateur})


class Supprimer(Page, crud.Supprimer):
    form_class = Formulaire

    def get_object(self):
        return Collaborateur.objects.get(pk=self.kwargs["idcollaborateur"])


class Onglet(CustomView):
    menu_code = "collaborateurs_toc"
    objet_singulier = "un collaborateur"
    liste_onglets = LISTE_ONGLETS

    def get_context_data(self, **kwargs):
        context = super(Onglet, self).get_context_data(**kwargs)
        context['page_titre'] = "Fiche collaborateur"
        context['liste_onglets'] = [dict_onglet for dict_onglet in self.liste_onglets if self.request.user.has_perm("core.collaborateur_%s" % dict_onglet["code"])]
        context['idcollaborateur'] = self.kwargs['idcollaborateur']
        context['collaborateur'] = Collaborateur.objects.get(pk=self.kwargs['idcollaborateur'])
        return context

    def test_func_page(self):
        # Vérifie que l'utilisateur a une permission d'accéder à ce collaborateur
        idcollaborateur = self.Get_idcollaborateur()
        if idcollaborateur and not Collaborateur.objects.filter((Q(groupes__superviseurs=self.request.user) | Q(groupes__superviseurs__isnull=True)), pk=idcollaborateur).exists():
            return False
        return True

    def Get_idcollaborateur(self):
        return self.kwargs.get('idcollaborateur', None)


class Resume(Onglet, DetailView):
    template_name = "collaborateurs/collaborateur_resume.html"

    def get_context_data(self, **kwargs):
        context = super(Resume, self).get_context_data(**kwargs)
        context['box_titre'] = self.object.nom
        context['box_introduction'] = ""
        context['onglet_actif'] = "resume"

        # Alertes
        context['pieces_fournir'] = utils_pieces_manquantes.Get_pieces_manquantes(collaborateur=context["collaborateur"], only_invalides=True)
        context['nbre_alertes'] = len(context['pieces_fournir'])

        # Notes du collaborateur
        conditions = (Q(utilisateur=self.request.user) | Q(utilisateur__isnull=True)) & (Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True))
        context['notes'] = Note.objects.filter(conditions, collaborateur_id=self.kwargs['idcollaborateur']).order_by("date_saisie")

        return context

    def get_object(self):
        return Collaborateur.objects.get(pk=self.kwargs['idcollaborateur'])
