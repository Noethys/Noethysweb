# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Activite, Inscription
from django.views.generic.detail import DetailView
from parametrage.forms.activites import Formulaire
from core.views.base import CustomView
from django.contrib import messages
from django.db.models import Q, Count


class Page(crud.Page):
    model = Activite
    url_liste = "activites_liste"
    url_ajouter = "activites_ajouter"
    url_modifier = "activites_resume"
    url_supprimer = "activites_supprimer"
    description_liste = "Voici ci-dessous la liste des activités."
    description_saisie = "Saisissez toutes les informations concernant l'activité à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une activité"
    objet_pluriel = "des activités"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
        {"label": "Ajouter avec assistant", "classe": "btn btn-default", "href": reverse_lazy("activites_assistant_liste"), "icone": "fa fa-magic"},
    ]


class Liste(Page, crud.Liste):
    model = Activite

    def get_queryset(self):
        # return Activite.objects.prefetch_related("groupes_activites").filter(self.Get_filtres("Q"), structure=self.request.user.structure_actuelle)
        return Activite.objects.prefetch_related("groupes_activites").filter(self.Get_filtres("Q"), structure__in=self.request.user.structures.all())
    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idactivite", "nom", "date_debut", "date_fin"]

        groupes = columns.TextColumn("Groupes d'activités", sources=None, processor='Get_groupes')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        periode = columns.DisplayColumn("Validité", sources="date_fin", processor='Get_validite')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idactivite", "nom", "periode", "groupes"]
            #hidden_columns = = ["idactivite"]
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ["-date_fin"]

        def Get_validite(self, instance, **kwargs):
            if not instance.date_fin or instance.date_fin.year == 2999:
                return "Validité illimitée"
            else:
                return "Du %s au %s" % (instance.date_debut.strftime('%d/%m/%Y'), instance.date_fin.strftime('%d/%m/%Y'))

        def Get_groupes(self, instance, *args, **kwargs):
            return ", ".join([groupe.nom for groupe in instance.groupes_activites.all()])


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

    def get_success_url(self):
        """ Renvoie vers la page résumé de l'activité """
        messages.add_message(self.request, messages.SUCCESS, 'Ajout enregistré')
        return reverse_lazy("activites_resume", kwargs={'idactivite': self.object.idactivite})


class Supprimer(Page, crud.Supprimer):
    form_class = Formulaire

    def get_object(self):
        return Activite.objects.get(pk=self.kwargs['idactivite'])




class Onglet(CustomView):
    menu_code = "activites_liste"
    liste_onglets = [
        {"code": "resume", "label": "Résumé", "icone": "fa-home", "url": "activites_resume"},
        {"rubrique": "Généralités"},
        {"code": "generalites", "label": "Généralités", "icone": "fa-info-circle", "url": "activites_generalites"},
        {"code": "responsables", "label": "Responsables", "icone": "fa-user", "url": "activites_responsables_liste"},
        {"code": "agrements", "label": "Agréments", "icone": "fa-file-text-o", "url": "activites_agrements_liste"},
        {"code": "groupes", "label": "Groupes", "icone": "fa-users", "url": "activites_groupes_liste"},
        {"code": "renseignements", "label": "Renseignements", "icone": "fa-check-circle-o", "url": "activites_renseignements"},
        {"rubrique": "Unités"},
        {"code": "unites_conso", "label": "Unités de consommation", "icone": "fa-table", "url": "activites_unites_conso_liste"},
        {"code": "unites_remplissage", "label": "Unités de remplissage", "icone": "fa-table", "url": "activites_unites_remplissage_liste"},
        {"rubrique": "Calendrier"},
        {"code": "calendrier", "label": "Calendrier", "icone": "fa-calendar", "url": "activites_calendrier"},
        {"code": "evenements", "label": "Evénements", "icone": "fa-calendar-times-o", "url": "activites_evenements_liste"},
        {"rubrique": "Tarifs"},
        {"code": "categories_tarifs", "label": "Catégories de tarifs", "icone": "fa-euro", "url": "activites_categories_tarifs_liste"},
        {"code": "noms_tarifs", "label": "Noms de tarifs", "icone": "fa-euro", "url": "activites_noms_tarifs_liste"},
        {"code": "tarifs", "label": "Tarifs", "icone": "fa-euro", "url": "activites_tarifs_liste"},
        {"rubrique": "Portail"},
        {"code": "portail_parametres", "label": "Paramètres", "icone": "fa-gear", "url": "activites_portail_parametres"},
        # {"code": "portail_unites", "label": "Unités de réservation", "icone": "fa-table", "url": "activites_portail_unites_liste"},
        {"code": "portail_periodes", "label": "Périodes de réservation", "icone": "fa-calendar", "url": "activites_portail_periodes_liste"},
    ]

    def get_context_data(self, **kwargs):
        context = super(Onglet, self).get_context_data(**kwargs)
        context['page_titre'] = "Gestion des activités"
        context['liste_onglets'] = self.liste_onglets
        context['activite'] = Activite.objects.get(pk=self.kwargs['idactivite'])
        return context

    def Get_idactivite(self):
        return self.kwargs.get('idactivite', None)





class Resume(Onglet, DetailView):
    template_name = "parametrage/activite_resume.html"

    def get_context_data(self, **kwargs):
        context = super(Resume, self).get_context_data(**kwargs)
        context['box_titre'] = self.object.nom
        context['box_introduction'] = "Ici résumé de l'activité..."
        context['onglet_actif'] = "resume"
        context['stats_inscrits'] = Inscription.objects.filter(activite_id=self.kwargs['idactivite']).count()
        context['stats_inscriptions'] = Inscription.objects.filter(activite_id=self.kwargs['idactivite']).values_list('date_debut__year', 'date_debut__month').annotate(nbre=Count('pk')).order_by('date_debut__year', 'date_debut__month')
        # context['stats_groupes'] = Inscription.objects.values('groupe__nom').filter(activite_id=self.kwargs['idactivite']).annotate(nbre=Count('pk'))
        # context['stats_categories'] = Inscription.objects.values('categorie_tarif__nom').filter(activite_id=self.kwargs['idactivite']).annotate(nbre=Count('pk'))
        return context

    def get_object(self):
        return Activite.objects.get(pk=self.kwargs['idactivite'])

