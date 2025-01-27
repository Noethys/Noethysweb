# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, decimal
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Sum
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Inscription, Activite, Cotisation, Groupe, Prestation, Ventilation
from core.utils import utils_texte, utils_dates
from fiche_individu.forms.individu_inscriptions import Formulaire


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
        if self.Get_groupe():
            condition &= Q(groupe=self.Get_groupe())
        return Inscription.objects.select_related("famille", "individu", "groupe", "categorie_tarif", "activite", "activite__structure").filter(self.Get_filtres("Q"), condition, activite=self.Get_activite())

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['box_titre'] = "Liste des inscriptions d'une activité"
        context["impression_titre"] = Activite.objects.get(pk=self.Get_activite()).nom if self.Get_activite() else ""
        context["impression_introduction"] = Groupe.objects.get(pk=self.Get_groupe()).nom if self.Get_groupe() else ""
        context["impression_conclusion"] = ""
        context["afficher_menu_brothers"] = True
        context["active_checkbox"] = True

        # Choix de l'activité
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

        # Choix du groupe
        context['liste_groupes'] = [(None, "Tous les groupes")]
        if self.Get_activite():
            context['liste_groupes'] += [(groupe.pk, groupe.nom) for groupe in Groupe.objects.filter(activite_id=int(self.Get_activite())).order_by("ordre")]
        context['groupe'] = int(self.Get_groupe()) if self.Get_groupe() else None

        context['url_supprimer_plusieurs'] = reverse_lazy(self.url_supprimer_plusieurs, kwargs={'activite': self.kwargs.get('activite', None), "listepk": "xxx"})
        return context

    def Get_activite(self):
        activite = self.kwargs.get("activite", None)
        if activite:
            activite = activite.replace("A", "")
            return int(activite)
        return None

    def Get_groupe(self):
        groupe = self.kwargs.get("groupe", None)
        if groupe:
            return int(groupe)
        return None

    def Get_afficher_obsoletes(self):
        return "A" in self.kwargs.get("activite", "")

    class datatable_class(MyDatatable):
        filtres = ["igenerique:individu", "fgenerique:famille", "idinscription", "date_debut", "date_fin", "activite__nom", "groupe__nom", "statut", "categorie_tarif__nom"]
        check = columns.CheckBoxSelectColumn(label="")
        actions = columns.TextColumn("Actions", sources=None, processor="Get_actions_speciales")
        groupe = columns.TextColumn("Groupe", sources=["groupe__nom"])
        categorie_tarif = columns.TextColumn("Catégorie de tarif", sources=["categorie_tarif__nom"])
        individu = columns.CompoundColumn("Individu", sources=["individu__nom", "individu__prenom"])
        famille = columns.TextColumn("Famille", sources=["famille__nom"])
        individu_ville = columns.TextColumn("Ville de l'individu", processor="Get_ville_individu")
        famille_ville = columns.TextColumn("Ville de la famille", processor="Get_ville_famille")
        date_naiss = columns.TextColumn("Date naiss.", processor='Get_date_naiss')
        age = columns.TextColumn("Age", sources=['Get_age'], processor="Get_age")
        mail = columns.CompoundColumn("Email", processor='Get_mail')
        portable = columns.CompoundColumn("Portable", processor='Get_mobile')
        tel_parents = columns.TextColumn("Tél responsables", sources=None, processor="Get_tel_parents")
        mail_parents = columns.TextColumn("Mail responsables", sources=None, processor="Get_mail_parents")
        num_cotisation = columns.TextColumn("N° adhésion", sources=None, processor="Get_num_cotisation")
        total = columns.TextColumn("Total", sources=[], processor="Get_total")
        solde = columns.TextColumn("Solde", sources=[], processor="Get_solde")
        mail_famille = columns.TextColumn("Email famille", processor='Get_mail_famille')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idinscription", "date_debut", "date_fin", "individu", "date_naiss", "age", "mail", "portable",
                       "famille", "tel_parents", "mail_parents", "mail_famille", "groupe", "categorie_tarif", "individu_ville",
                       "famille_ville", "num_cotisation", "statut", "total", "solde"]
            hidden_columns = ["idinscription", "date_debut", "date_fin", "mail", "famille", "categorie_tarif", "individu_ville",
                              "famille_ville", "num_cotisation", "total", "solde", "mail_famille"]
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

        def Get_date_naiss(self, instance, *args, **kwargs):
            return utils_dates.ConvertDateToFR(instance.individu.date_naiss)

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

        def Get_mail(self, instance, *args, **kwargs):
            return instance.individu.mail

        def Get_mobile(self, instance, *args, **kwargs):
            return instance.individu.tel_mobile

        def Get_ville_individu(self, instance, *args, **kwargs):
            return instance.individu.ville_resid

        def Get_ville_famille(self, instance, *args, **kwargs):
            return instance.famille.ville_resid

        def Get_tel_parents(self, instance, *args, **kwargs):
            return self.Calc_tel_parents(idindividu=instance.individu_id, idfamille=instance.famille_id)

        def Get_mail_parents(self, instance, *args, **kwargs):
            return self.Calc_mail_parents(idindividu=instance.individu_id, idfamille=instance.famille_id)

        def Get_mail_famille(self, instance, *args, **kwargs):
            return instance.famille.mail

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

        def Get_solde(self, instance, *args, **kwargs):
            # Calcul du solde de l'activité pour l'individu
            if not hasattr(self, "dict_soldes"):
                self.Calc_solde(instance)
            solde = self.dict_soldes.get((instance.famille_id, instance.individu_id), decimal.Decimal(0))
            if solde == decimal.Decimal(0):
                couleur = "success"
            elif solde > decimal.Decimal(0):
                couleur = "info"
            else:
                couleur = "danger"
            return """<span class='badge badge-%s'>%s</span>""" % (couleur, utils_texte.Formate_montant(solde))

        def Get_total(self, instance, *args, **kwargs):
            # Calcul du total de l'activité pour l'individu
            if not hasattr(self, "dict_prestations"):
                self.Calc_solde(instance)
            total = self.dict_prestations.get((instance.famille_id, instance.individu_id), decimal.Decimal(0))
            return utils_texte.Formate_montant(total)

        def Calc_solde(self, instance=None):
            dict_ventilations = {temp["prestation_id"]: temp["total"] for temp in Ventilation.objects.values("prestation_id").filter(prestation__activite_id=instance.activite_id).annotate(total=Sum("montant"))}
            self.dict_soldes = {}
            self.dict_prestations = {}
            for prestation in Prestation.objects.values("famille_id", "individu_id", "pk").filter(activite_id=instance.activite_id).annotate(total=Sum("montant")):
                key = (prestation["famille_id"], prestation["individu_id"])
                self.dict_soldes.setdefault(key, decimal.Decimal(0))
                self.dict_soldes[key] += dict_ventilations.get(prestation["pk"], decimal.Decimal(0)) - prestation["total"]
                self.dict_prestations.setdefault(key, decimal.Decimal(0))
                self.dict_prestations[key] += prestation["total"]
            del dict_ventilations


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass

class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
    pass
