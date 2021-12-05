# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Consommation


class Page(crud.Page):
    model = Consommation
    url_liste = "liste_consommations"
    menu_code = "liste_consommations"
    description_liste = "Voici ci-dessous la liste des consommations."
    description_saisie = "Saisissez toutes les informations concernant la consommation à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une consommation"
    objet_pluriel = "des consommations"
    # url_supprimer_plusieurs = "consommations_supprimer_plusieurs"


class Liste(Page, crud.Liste):
    model = Consommation

    def get_queryset(self):
        return Consommation.objects.select_related("activite", "inscription__famille", "individu", "unite", "groupe", "categorie_tarif", "prestation").filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        # context['active_checkbox'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["ipresent:individu", "fpresent:famille", "idconso", "date_saisie", "date", "unite__nom", "groupe__nom", "etat", "activite__nom", "inscription__famille__nom",
                   "individu__nom", "individu__prenom", "heure_debut", "heure_fin", "quantite", "prestation__idprestation", "categorie_tarif__nom"]
        # check = columns.CheckBoxSelectColumn(label="")
        activite = columns.TextColumn("Activité", sources=['activite__nom'])
        unite = columns.TextColumn("Unité", sources=['unite__nom'])
        groupe = columns.TextColumn("Groupe", sources=['groupe__nom'])
        categorie_tarif = columns.TextColumn("Catégorie", sources=['categorie_tarif__nom'])
        individu = columns.CompoundColumn("Individu", sources=['individu__nom', 'individu__prenom'])
        famille = columns.TextColumn("Famille", sources=['inscription__famille__nom'])
        etat = columns.TextColumn("Etat", sources=['etat'], processor='Get_etat')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = [#"check",
                       "idconso", "date_saisie", "individu", "famille", "date", "unite", "groupe", "activite", "etat", "heure_debut", "heure_fin",
                       "quantite", "categorie_tarif", "prestation"]
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


# Supprimer_plusieurs non fonctionnel : il faut coder la suppression de la prestation en même temps
# class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
#     pass
#
#     def Check_protections(self, objets=[]):
#         protections = []
#         for conso in objets:
#             # Vérifie l'état de la conso
#             if conso.etat in ("present", "absenti", "absentj"):
#                 protections.append("ID%d=%s" % (conso.pk, conso.etat))
#             # Vérifie si la conso est facturée
#             if conso.prestation.facture_id:
#                 protections.append("ID%d=Facturé" % conso.pk)
#         return protections
