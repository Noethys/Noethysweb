# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Cotisation


class Page(crud.Page):
    model = Cotisation


class Liste(Page, crud.Liste):
    model = Cotisation
    menu_code = "liste_cotisations_disponibles"

    def get_queryset(self):
        return Cotisation.objects.select_related('famille', 'individu', 'type_cotisation', 'unite_cotisation').filter(self.Get_filtres("Q"), depot_cotisation__isnull=True)

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Liste des adhésions non déposées"
        context['box_titre'] = "Liste des adhésions non déposées"
        context['box_introduction'] = "Voici ci-dessous la liste des adhésions qui ne sont pas incluses dans des dépôts."
        context['afficher_menu_brothers'] = True
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ["ipresent:individu", "fpresent:famille", "idcotisation", "date_saisie", "date_creation_carte", 'famille__nom', 'individu__nom', 'individu__prenom', "numero", "date_debut", "date_fin", "observations", "type_cotisation__nom", "unite_cotisation__nom"]

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        individu = columns.CompoundColumn("Individu", sources=['individu__nom', 'individu__prenom'])
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        nom_cotisation = columns.TextColumn("Nom", sources=['type_cotisation__nom', 'unite_cotisation__nom'], processor='Get_nom_cotisation')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idcotisation', 'date_debut', 'date_fin', 'famille', 'individu', 'nom_cotisation', 'numero']
            #hidden_columns = = ["idcotisation"]
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


