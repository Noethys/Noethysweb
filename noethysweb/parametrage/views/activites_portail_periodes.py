# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers, Deplacer_lignes
from core.views import crud
from parametrage.views.activites import Onglet
from core.models import PortailPeriode, Activite
from parametrage.forms.activites_portail_periodes import Formulaire
from django.db.models import Q


class Page(Onglet):
    model = PortailPeriode
    url_liste = "activites_portail_periodes_liste"
    url_ajouter = "activites_portail_periodes_ajouter"
    url_modifier = "activites_portail_periodes_modifier"
    url_supprimer = "activites_portail_periodes_supprimer"
    description_liste = "Vous pouvez saisir ici des périodes de réservation pour l'activité. Elles sont nécessaires si vous souhaitez permettre aux usagers d'enregistrer des réservations depuis le portail famille."
    description_saisie = "Saisissez toutes les informations concernant la période de réservation à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une période de réservation"
    objet_pluriel = "des périodes de réservation"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Périodes de réservation"
        context['onglet_actif'] = "portail_periodes"
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
    model = PortailPeriode
    template_name = "parametrage/activite_liste.html"

    def get_queryset(self):
        return PortailPeriode.objects.filter(Q(activite=self.Get_idactivite()) & self.Get_filtres("Q"))

    class datatable_class(MyDatatable):
        filtres = ['idperiode', 'date_debut', 'date_fin', 'nom']
        affichage = columns.DisplayColumn("Affichage", sources="affichage_date_debut", processor='Get_affichage')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idperiode', 'date_debut', 'date_fin', 'nom', 'affichage']
            ordering = ['date_debut']
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }

        def Get_affichage(self, instance, **kwargs):
            if instance.affichage == "TOUJOURS":
                return "Toujours afficher"
            elif instance.affichage == "JAMAIS":
                return "Ne pas afficher"
            else:
                return "Du %s au %s" % (instance.affichage_date_debut.strftime("%d/%m/%Y %H:%M"), instance.affichage_date_fin.strftime("%d/%m/%Y %H:%M"))

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idactivite dans les boutons d'actions """
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.activite.idactivite, instance.pk])),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.activite.idactivite, instance.pk])),
            ]
            return self.Create_boutons_actions(html)



class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "parametrage/activite_edit.html"

class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "parametrage/activite_edit.html"

class Supprimer(Page, crud.Supprimer):
    template_name = "parametrage/activite_delete.html"
