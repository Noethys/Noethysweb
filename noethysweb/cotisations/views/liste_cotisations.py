# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Cotisation
from core.utils import utils_dates
from django.db.models import Q


class Page(crud.Page):
    model = Cotisation
    url_liste = "cotisations_liste"
    description_liste = "Voici ci-dessous la liste des adhésions."
    description_saisie = "Saisissez toutes les informations concernant l'adhésion à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une adhésion"
    objet_pluriel = "des adhésions"
    url_supprimer_plusieurs = "cotisations_supprimer_plusieurs"



class Liste(Page, crud.Liste):
    model = Cotisation

    def get_queryset(self):
        condition = (Q(type_cotisation__structure__in=self.request.user.structures.all()) | Q(type_cotisation__structure__isnull=True))
        return Cotisation.objects.select_related('famille', 'individu', 'type_cotisation', 'type_cotisation__structure', 'unite_cotisation', 'depot_cotisation').filter(self.Get_filtres("Q"), condition)

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['active_checkbox'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["ipresent:individu", "fpresent:famille", "iscolarise:individu", "fscolarise:famille", "idcotisation", "date_saisie", "date_creation_carte", 'famille__nom', 'individu__nom', 'individu__prenom', "numero", "date_debut", "date_fin", "observations", "type_cotisation__nom", "unite_cotisation__nom", "depot_cotisation__date"]

        check = columns.CheckBoxSelectColumn(label="")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        individu = columns.CompoundColumn("Individu", sources=['individu__nom', 'individu__prenom'])
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        nom_cotisation = columns.TextColumn("Nom", sources=['type_cotisation__nom', 'unite_cotisation__nom'], processor='Get_nom_cotisation')
        depot = columns.TextColumn("Dépôt", sources=['depot_cotisation__date'], processor='Get_date_depot')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', 'idcotisation', 'date_debut', 'date_fin', 'famille', 'individu', 'nom_cotisation', 'numero', 'depot']
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            labels = {
                "date_debut": "Début",
                "date_fin": "Fin",
            }
            ordering = ["date_debut"]

        def Get_nom_cotisation(self, instance, *args, **kwargs):
            if instance.prestation:
                return instance.prestation.label
            else:
                return "%s - %s" % (instance.type_cotisation.nom, instance.unite_cotisation.nom)

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idindividu dans les boutons d'actions """
            html = [
                self.Create_bouton_imprimer(url=reverse("famille_voir_cotisation", kwargs={"idfamille": instance.famille_id, "idcotisation": instance.pk}), title="Imprimer ou envoyer par email l'adhésion"),
            ]
            return self.Create_boutons_actions(html)

        def Get_date_depot(self, instance, *args, **kwargs):
            if instance.depot_cotisation:
                return utils_dates.ConvertDateToFR(instance.depot_cotisation.date)
            return ""


class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
    pass
