# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.urls import reverse
from django.http import JsonResponse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Consommation
from consommations.forms.liste_consommations import Formulaire


def Dissocier_prestation(request):
    """ Dissocier les prestations des consommations cochées """
    liste_lignes = json.loads(request.POST["liste_lignes"])
    Consommation.objects.filter(pk__in=liste_lignes).update(prestation=None)
    return JsonResponse({"resultat": "ok"})


class Page(crud.Page):
    model = Consommation
    url_liste = "liste_consommations"
    menu_code = "liste_consommations"
    url_modifier = "liste_consommations_modifier"
    url_supprimer = "liste_consommations_supprimer"
    description_liste = "Voici ci-dessous la liste des consommations."
    description_saisie = "Saisissez toutes les informations concernant la consommation à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une consommation"
    objet_pluriel = "des consommations"
    url_supprimer_plusieurs = "consommations_supprimer_plusieurs"


class Liste(Page, crud.Liste):
    model = Consommation

    def get_queryset(self):
        return Consommation.objects.select_related("activite", "inscription__famille", "individu", "unite", "groupe", "categorie_tarif", "prestation").filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        context['active_checkbox'] = True
        context['boutons_coches'] = json.dumps([
            {"id": "bouton_dissocier_prestation", "action": """action_bouton_coche("%s")""" % reverse("ajax_consommations_dissocier_prestation"), "title": "Dissocier la prestation", "label": "Dissocier la prestation"},
        ])
        return context

    class datatable_class(MyDatatable):
        filtres = ["igenerique:individu", "fgenerique:inscription__famille", "idconso", "date_saisie", "date", "unite__nom", "groupe__nom", "etat", "activite__nom",
                   "heure_debut", "heure_fin", "quantite", "prestation__idprestation", "categorie_tarif__nom", "prestation__label", "prestation__montant"]
        check = columns.CheckBoxSelectColumn(label="")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        activite = columns.TextColumn("Activité", sources=['activite__nom'])
        unite = columns.TextColumn("Unité", sources=['unite__nom'])
        groupe = columns.TextColumn("Groupe", sources=['groupe__nom'])
        categorie_tarif = columns.TextColumn("Catégorie", sources=['categorie_tarif__nom'])
        individu = columns.CompoundColumn("Individu", sources=['individu__nom', 'individu__prenom'])
        famille = columns.TextColumn("Famille", sources=['inscription__famille__nom'])
        etat = columns.TextColumn("Etat", sources=['etat'], processor='Get_etat')
        prestation = columns.TextColumn("ID Prestation", sources=['prestation__idprestation'])
        label_prestation = columns.TextColumn("Label prestation", sources=["prestation__label"])
        montant_prestation = columns.TextColumn("Montant prestation", sources=["prestation__montant"])
        ville_resid = columns.TextColumn("Ville", sources=None, processor="Get_ville_resid")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check","idconso", "date_saisie", "individu", "famille", "date", "unite", "groupe", "activite", "etat", "heure_debut", "heure_fin",
                       "quantite", "categorie_tarif", "prestation", "label_prestation", "montant_prestation", "ville_resid", "actions"]
            processors = {
                "date": helpers.format_date('%d/%m/%Y'),
                "date_saisie": helpers.format_date('%d/%m/%Y %H:%M'),
                "montant_prestation": "Formate_montant_standard",
            }
            hidden_columns = ["prestation", "label_prestation", "montant_prestation", "ville_resid"]
            ordering = ["date_saisie"]

        def Get_ville_resid(self, instance, *args, **kwargs):
            return instance.individu.ville_resid

        def Get_etat(self, instance, **kwargs):
            return instance.get_etat_display()


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):

    def Check_protections(self, objet=None):
        protections = []
        if objet.etat in ("present", "absenti", "absentj"):
            protections.append("La consommation est pointée")
        if objet.prestation:
            protections.append("Une prestation est associée")
        return protections


class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):

    def Check_protections(self, objets=[]):
        protections = []
        for conso in objets:
            if conso.etat in ("present", "absenti", "absentj"):
                protections.append("La consommation ID%d est pointée %s" % (conso.pk, conso.etat))
            if conso.prestation:
                protections.append("La consommation ID%d est associée à une prestation" % conso.pk)
        return protections
