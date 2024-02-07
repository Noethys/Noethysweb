# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Prestation
from core.utils import utils_preferences
from django.db.models import Q



class Page(crud.Page):
    model = Prestation
    url_liste = "liste_prestations"
    menu_code = "liste_prestations"
    description_liste = "Voici ci-dessous la liste des prestations."
    description_saisie = "Saisissez toutes les informations concernant la prestation à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une prestation"
    objet_pluriel = "des prestations"
    url_supprimer_plusieurs = "prestations_supprimer_plusieurs"


class Liste(Page, crud.Liste):
    model = Prestation

    def get_queryset(self):
        #Filtrage en fonction des autorisations
        activites_autorisees = self.request.user.structures.all()
        return Prestation.objects.select_related('activite', 'famille', 'individu', 'tarif', 'facture').filter(self.Get_filtres("Q"), activite__structure__in=activites_autorisees)

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        context['active_checkbox'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["ipresent:individu", "fpresent:famille", "iscolarise:individu", "fscolarise:famille", "idprestation", "date", "label", "montant", "activite__nom", "famille__nom", "individu__nom", "individu__prenom",
                   "tarif__idtarif", "tarif__date_debut", "facture__idfacture"]

        check = columns.CheckBoxSelectColumn(label="")
        activite = columns.TextColumn("Activité", sources=['activite__nom'])
        individu = columns.CompoundColumn("Individu", sources=['individu__nom', 'individu__prenom'])
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        tarif = columns.TextColumn("ID Tarif", sources=['tarif__idtarif'])
        tarif_date_debut = columns.TextColumn("Tarif Début", sources=['tarif__date_debut'], processor=helpers.format_date("%d/%m/%Y"))
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', "idprestation", "date", "label", "montant", "activite", "famille", "individu", "tarif", "tarif_date_debut", "facture"]
            processors = {
                "date": helpers.format_date("%d/%m/%Y"),
                "montant": "Formate_montant_standard",
            }
            ordering = ["date"]
            
        #Bouton modification de la prestation 
        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_modifier(url=reverse("famille_prestations_modifier", kwargs={"idfamille": instance.famille_id, "pk": instance.pk})),
                ]

            return self.Create_boutons_actions(html)
            
class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
    pass
