# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Rappel
from core.utils import utils_texte



class Page(crud.Page):
    model = Rappel
    url_liste = "rappels_liste"
    menu_code = "rappels_liste"
    description_liste = "Voici ci-dessous la liste des lettres de rappel générées."
    objet_singulier = "une lettre de rappel"
    objet_pluriel = "des lettre de rappel"



class Liste(Page, crud.Liste):
    model = Rappel

    def get_queryset(self):
        return Rappel.objects.select_related('famille', 'lot').filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["fpresent:famille", 'idrappel', 'date_edition', 'numero', 'famille', 'date_reference', 'solde', 'date_min', 'date_max', 'lot__nom']

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        solde = columns.TextColumn("Solde", sources=['solde'], processor='Get_solde')
        lot = columns.TextColumn("Lot", sources=['lot__nom'])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idrappel', 'date_edition', 'numero', 'famille', 'solde', 'date_max', 'lot']
            #hidden_columns = = ["idrappel"]
            processors = {
                'date_edition': helpers.format_date('%d/%m/%Y'),
                'date_max': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ["date_edition"]

        def Get_solde(self, instance, **kwargs):
            return utils_texte.Formate_montant(instance.solde)

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_imprimer(url=reverse("famille_voir_rappel", kwargs={"idfamille": instance.famille_id, "idrappel": instance.pk}), title="Imprimer ou envoyer par email la lettre de rappel"),
            ]
            return self.Create_boutons_actions(html)


