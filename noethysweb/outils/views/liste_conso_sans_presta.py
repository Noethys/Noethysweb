# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.db.models import Q
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Consommation


class Page(crud.Page):
    model = Consommation
    url_liste = "liste_conso_sans_presta"
    menu_code = "liste_conso_sans_presta"
    description_liste = "Voici ci-dessous la liste des consommations sans prestations associées."
    objet_singulier = "une consommation"
    objet_pluriel = "des consommations sans prestations associées"
    url_supprimer_plusieurs = "liste_conso_sans_presta_supprimer_plusieurs"


class Liste(Page, crud.Liste):
    model = Consommation

    def get_queryset(self):
        conditions = Q(prestation__isnull=True)
        return Consommation.objects.select_related("activite", "inscription__famille", "individu", "unite", "groupe", "categorie_tarif").filter(conditions, self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        context['active_checkbox'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["igenerique:individu", "fgenerique:inscription__famille", "idconso", "date_saisie", "date", "unite__nom", "groupe__nom", "etat", "activite__nom", "heure_debut", "heure_fin", "quantite", "categorie_tarif__nom"]
        check = columns.CheckBoxSelectColumn(label="")
        activite = columns.TextColumn("Activité", sources=['activite__nom'])
        unite = columns.TextColumn("Unité", sources=['unite__nom'])
        groupe = columns.TextColumn("Groupe", sources=['groupe__nom'])
        categorie_tarif = columns.TextColumn("Catégorie", sources=['categorie_tarif__nom'])
        individu = columns.CompoundColumn("Individu", sources=['individu__nom', 'individu__prenom'])
        famille = columns.TextColumn("Famille", sources=['inscription__famille__nom'])
        etat = columns.TextColumn("Etat", sources=['etat'], processor='Get_etat')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idconso", "date_saisie", "individu", "famille", "date", "unite", "groupe", "activite", "etat", "heure_debut", "heure_fin", "quantite", "categorie_tarif"]
            processors = {
                "date": helpers.format_date('%d/%m/%Y'),
                "date_saisie": helpers.format_date('%d/%m/%Y %H:%M'),
            }
            ordering = ["date_saisie"]

        def Get_etat(self, instance, **kwargs):
            if instance.etat == "reservation": return "Réservation"
            if instance.etat == "attente": return "Attente"
            if instance.etat == "refus": return "Refus"
            if instance.etat == "present": return "Présent"
            if instance.etat == "absenti": return "Absence injustifiée"
            if instance.etat == "absentj": return "Absence justifiée"
            return "?"


class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):

    def Check_protections(self, objets=[]):
        protections = []
        for conso in objets:
            # Vérifie l'état de la conso
            if conso.etat in ("present", "absenti", "absentj"):
                protections.append("ID%d=%s" % (conso.pk, conso.etat))
        return protections
