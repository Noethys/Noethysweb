# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Inscription, Activite, Rattachement, Cotisation
from fiche_individu.forms.individu_inscriptions import Formulaire
from django.db.models import Q


class Page(crud.Page):
    model = Inscription
    url_liste = "inscriptions_activite_liste"
    url_modifier = "inscriptions_activite_modifier"
    url_supprimer = "inscriptions_activite_supprimer"
    url_supprimer_plusieurs = "inscriptions_activite_supprimer_plusieurs"
    description_liste = "Sélectionnez une activité dans la liste déroulante afin d'obtenir la liste des inscrits. Vous ne pouvez accéder qu'aux inscriptions associées à vos structures. Cliquez sur le bouton <i class='fa fa-eye-slash'></i> si vous souhaitez afficher d'autres colonnes disponibles."
    description_saisie = "Saisissez toutes les informations concernant l'inscription à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une inscription"
    objet_pluriel = "des inscriptions"


class Liste(Page, crud.Liste):
    template_name = "individus/inscriptions_activite_liste.html"
    model = Inscription

    def get_queryset(self):
        condition = Q(activite__structure__in=self.request.user.structures.all())
        return Inscription.objects.select_related("famille", "individu", "groupe", "categorie_tarif", "activite", "activite__structure").filter(self.Get_filtres("Q"), condition, activite=self.Get_activite())

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['box_titre'] = "Liste des inscriptions d'une activité"
        context["impression_introduction"] = ""
        context["impression_conclusion"] = ""
        context["afficher_menu_brothers"] = True
        context["active_checkbox"] = True

        context['afficher_obsoletes'] = self.Get_afficher_obsoletes()
        context['activite'] = int(self.Get_activite()) if self.Get_activite() else None
        condition = Q()
        if not self.Get_afficher_obsoletes():
            condition &= (Q(date_fin__isnull=False) & Q(date_fin__gte=datetime.date.today()))
        liste_activites = []
        for activite in Activite.objects.filter(self.Get_condition_structure(), condition).order_by("-date_fin", "nom"):
            if activite.date_fin.year == 2999:
                liste_activites.append((activite.pk, "%s - Activité illimitée" % activite.nom))
            elif activite.date_fin:
                liste_activites.append((activite.pk, "%s - Du %s au %s" % (activite.nom, activite.date_debut.strftime("%d/%m/%Y"), activite.date_fin.strftime("%d/%m/%Y"))))
            else:
                liste_activites.append((activite.pk, "%s - A partir du %s" % (activite.nom, activite.date_debut.strftime("%d/%m/%Y"))))
        context['liste_activites'] = [(None, "--------")] + liste_activites

        context['url_supprimer_plusieurs'] = reverse_lazy(self.url_supprimer_plusieurs, kwargs={'activite': self.kwargs.get('activite', None), "listepk": "xxx"})
        return context

    def Get_activite(self):
        activite = self.kwargs.get("activite", None)
        if activite:
            activite = activite.replace("A", "")
            return activite
        return None

    def Get_afficher_obsoletes(self):
        return "A" in self.kwargs.get("activite", "")

    class datatable_class(MyDatatable):
        filtres = ["ipresent:individu", "fpresent:famille", "iscolarise:individu", "fscolarise:famille", "idinscription", "famille__nom", "individu__nom", "individu__prenom", "individu__ville_resid", "famille__ville_resid", "date_debut", "date_fin", "activite__nom", "groupe__nom", "statut", "categorie_tarif__nom"]
        check = columns.CheckBoxSelectColumn(label="")
        actions = columns.TextColumn("Actions", sources=None, processor="Get_actions_speciales")
        groupe = columns.TextColumn("Groupe", sources=["groupe__nom"])
        categorie_tarif = columns.TextColumn("Catégorie de tarif", sources=["categorie_tarif__nom"])
        individu = columns.CompoundColumn("Individu", sources=["individu__nom", "individu__prenom"])
        famille = columns.TextColumn("Famille", sources=["famille__nom"])
        individu_ville = columns.TextColumn("Ville de l'individu", processor="Get_ville_individu")
        famille_ville = columns.TextColumn("Ville de la famille", processor="Get_ville_famille")
        date_naiss = columns.TextColumn("Date naiss.", sources=["individu__date_naiss"], processor=helpers.format_date("%d/%m/%Y"))
        age = columns.TextColumn("Age", sources=['Get_age'], processor="Get_age")
        mail = columns.CompoundColumn("Email", sources=["individu__mail"])
        portable = columns.CompoundColumn("Portable", sources=["individu__tel_mobile"])
        tel_parents = columns.TextColumn("Tél responsables", sources=None, processor="Get_tel_parents")
        num_cotisation = columns.TextColumn("N° adhésion", sources=None, processor="Get_num_cotisation")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idinscription", "date_debut", "date_fin", "individu", "date_naiss", "age", "mail", "portable", "famille", "tel_parents", "groupe", "categorie_tarif", "individu_ville", "famille_ville", "num_cotisation", "statut"]
            hidden_columns = ["idinscription", "date_debut", "date_fin", "mail", "famille", "categorie_tarif", "individu_ville", "famille_ville", "num_cotisation"]
            page_length = 100
            processors = {
                "date_debut": helpers.format_date("%d/%m/%Y"),
                "date_fin": helpers.format_date("%d/%m/%Y"),
                "statut": "Formate_statut",
            }
            labels = {
                "date_debut": "Début",
                "date_fin": "Fin",
            }
            ordering = ["individu"]

        def Get_age(self, instance, *args, **kwargs):
            return instance.individu.Get_age()

        def Formate_statut(self, instance, *args, **kwargs):
            if instance.statut == "attente":
                return "<i class='fa fa-hourglass-2 text-yellow'></i> Attente"
            elif instance.statut == "refus":
                return "<i class='fa fa-times-circle text-red'></i> Refus"
            else:
                return "<i class='fa fa-check-circle-o text-green'></i> Valide"

        def Get_actions_speciales(self, instance, *args, **kwargs):
            view = kwargs["view"]
            html = [
                self.Create_bouton_modifier(url=reverse(view.url_modifier, args=[instance.activite_id, instance.pk])),
                self.Create_bouton_supprimer(url=reverse(view.url_supprimer, args=[instance.activite_id, instance.pk])),
                self.Create_bouton(url=reverse("famille_resume", args=[instance.famille_id]), title="Ouvrir la fiche famille", icone="fa-users"),
            ]
            return self.Create_boutons_actions(html)

        def Get_ville_individu(self, instance, *args, **kwargs):
            return instance.individu.ville_resid

        def Get_ville_famille(self, instance, *args, **kwargs):
            return instance.famille.ville_resid

        def Get_tel_parents(self, instance, *args, **kwargs):
            # Importation initiale des parents
            if not hasattr(self, "dict_parents"):
                self.dict_parents = {}
                self.liste_enfants = []
                for rattachement in Rattachement.objects.select_related("individu").all():
                    if rattachement.categorie == 1:
                        self.dict_parents.setdefault(rattachement.famille_id, [])
                        self.dict_parents[rattachement.famille_id].append(rattachement.individu)
                    if rattachement.categorie == 2:
                        self.liste_enfants.append((rattachement.famille_id, rattachement.individu_id))

            # Recherche des parents
            liste_tel = []
            if (instance.famille_id, instance.individu_id) in self.liste_enfants:
                for individu in self.dict_parents.get(instance.famille_id, []):
                    if individu.tel_mobile and individu != instance.individu:
                        liste_tel.append("%s : %s" % (individu.prenom, individu.tel_mobile))

            return " | ".join(liste_tel)

        def Get_num_cotisation(self, instance, *args, **kwargs):
            # Importation initiale des cotisations
            if not hasattr(self, "dict_cotisations"):
                self.dict_cotisations = {}
                for cotisation in Cotisation.objects.filter(date_debut__lte=instance.activite.date_fin, date_fin__gte=instance.activite.date_debut).order_by("-date_debut"):
                    self.dict_cotisations.setdefault(cotisation.famille_id, [])
                    self.dict_cotisations[cotisation.famille_id].append(cotisation)

            # Recherche d'une cotisation valable durant l'activité
            for cotisation in self.dict_cotisations.get(instance.famille_id, []):
                if not cotisation.individu_id or cotisation.individu_id == instance.individu_id:
                    return cotisation.numero

            return None


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass

class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
    pass
