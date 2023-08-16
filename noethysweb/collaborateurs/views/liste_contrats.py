# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse
from django.db.models import Q
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import ContratCollaborateur


class Page(crud.Page):
    model = ContratCollaborateur
    url_liste = "contrats_liste"
    description_liste = "Voici ci-dessous la liste des contrats."
    description_saisie = "Saisissez toutes les informations concernant le contrat à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un contrat"
    objet_pluriel = "des contrats"


class Liste(Page, crud.Liste):
    model = ContratCollaborateur

    def get_queryset(self):
        conditions = (Q(collaborateur__groupes__superviseurs=self.request.user) | Q(collaborateur__groupes__superviseurs__isnull=True))
        return ContratCollaborateur.objects.select_related("collaborateur", "type_poste").filter(conditions, self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ["idcontrat", "date_debut", "date_fin", "collaborateur", "type_poste"]
        collaborateur = columns.TextColumn("Collaborateur", sources=["collaborateur__nom", "collaborateur__prenom"], processor='Get_nom_collaborateur')
        type_poste = columns.TextColumn("Poste", sources=["type_poste__nom"], processor='Get_nom_type_poste')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idcontrat", "date_debut", "date_fin", "collaborateur", "type_poste"]
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            labels = {
                "date_debut": "Début",
                "date_fin": "Fin",
            }
            ordering = ["date_debut"]

        def Get_nom_collaborateur(self, instance, *args, **kwargs):
            return instance.collaborateur.Get_nom()

        def Get_nom_type_poste(self, instance, *args, **kwargs):
            return instance.type_poste.nom

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_modifier(url=reverse("collaborateur_contrats_modifier", kwargs={"idcollaborateur": instance.collaborateur_id, "pk": instance.pk})),
                self.Create_bouton_supprimer(url=reverse("collaborateur_contrats_supprimer", kwargs={"idcollaborateur": instance.collaborateur_id, "pk": instance.pk})),
                self.Create_bouton_word(url=reverse("collaborateur_voir_contrat", kwargs={"idcollaborateur": instance.collaborateur_id, "idcontrat": instance.pk})),
            ]
            return self.Create_boutons_actions(html)
