# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from decimal import Decimal
from django.urls import reverse_lazy, reverse
from django.db.models import Sum, Q, Min, Max, F, OuterRef, Subquery, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.contrib import messages
from django.views.generic.detail import DetailView
from django.core.cache import cache
from core.views.base import CustomView
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Famille, Note, Rattachement, CATEGORIES_RATTACHEMENT, Prestation, Reglement, PortailMessage, Inscription, Facture, Ventilation
from individus.utils import utils_pieces_manquantes, utils_informations_manquantes, utils_vaccinations, utils_assurances
from fiche_individu.forms.individu import Formulaire
from fiche_famille.utils.utils_famille import LISTE_ONGLETS
from fiche_famille.utils import utils_transfert_familles
from cotisations.utils import utils_cotisations_manquantes


def Definir_titulaire(request):
    # Récupération des données du formulaire
    idrattachement = int(request.POST.get("idrattachement"))
    rattachement = Rattachement.objects.get(pk=idrattachement)

    # Vérifie qu'il reste au moins un titulaire dans la famille
    if rattachement.titulaire == True:
        titulaires = Rattachement.objects.filter(famille=rattachement.famille, titulaire=True)
        if len(titulaires) <= 1:
            messages.add_message(request, messages.ERROR, "Changement de titulaire impossible : Vous devez conserver au moins un titulaire dans la famille !")
            return JsonResponse({"success": False})

    # Inversion de la valeur titulaire
    rattachement.titulaire = not rattachement.titulaire
    rattachement.save()

    # MAJ de la fiche famille
    rattachement.famille.Maj_infos()

    messages.add_message(request, messages.SUCCESS, 'Modification enregistrée')
    return JsonResponse({"success": True})


def Changer_categorie(request):
    # Récupération des données du formulaire
    idrattachement = int(request.POST.get("idrattachement"))
    categorie = int(request.POST.get("categorie"))

    rattachement = Rattachement.objects.get(pk=idrattachement)

    # Vérifie qu'il reste au moins un titulaire dans la famille
    if rattachement.titulaire == True:
        titulaires = Rattachement.objects.filter(famille=rattachement.famille, titulaire=True)
        if len(titulaires) <= 1:
            messages.add_message(request, messages.ERROR, "Changement de catégorie impossible : Vous devez conserver au moins un titulaire dans la famille !")
            return JsonResponse({"success": False})

    # Vérifie qu'il reste au moins un représentant dans la famille
    if rattachement.categorie == 1:
        representants = Rattachement.objects.filter(famille=rattachement.famille, categorie=1)
        if len(representants) == 1:
            messages.add_message(request, messages.ERROR, "Changement de catégorie impossible : Vous devez conserver au moins un représentant dans la famille !")
            return JsonResponse({"success": False})

    # Inversion de la valeur titulaire
    rattachement.categorie = categorie

    if categorie in (2, 3):
        # Conversion en enfant ou en contact
        rattachement.titulaire = False
    if categorie == 1:
        # Conversion en représentant
        rattachement.titulaire = True
        messages.add_message(request, messages.INFO, "Notez que cet individu a été automatiquement défini comme titulaire du dossier")

    rattachement.save()

    # MAJ de la fiche famille
    rattachement.famille.Maj_infos()

    messages.add_message(request, messages.SUCCESS, 'Modification enregistrée')
    return JsonResponse({"success": True})


class Page(crud.Page):
    model = Famille
    url_liste = "famille_liste"
    url_ajouter = "famille_ajouter"
    url_modifier = "famille_resume"
    url_supprimer = "famille_supprimer"
    description_liste = "Voici ci-dessous la liste des familles."
    description_saisie = "Saisissez toutes les informations concernant la famille à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une famille"
    objet_pluriel = "des familles"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = Famille
    template_name = "fiche_famille/familles_liste_transfert.html"

    def get_queryset(self):
        return Famille.objects.filter(self.Get_filtres("Q"))

    def Transfert_autorise(self):
        """ Export et import de fiches familles : réservés aux super-utilisateurs """
        return self.request.user.is_superuser

    def get_datatable_class(self):
        # Colonne de cases à cocher uniquement pour ceux qui peuvent exporter
        return self.datatable_class_transfert if self.Transfert_autorise() else self.datatable_class

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        if self.Transfert_autorise():
            context['transfert_autorise'] = True
            context['active_checkbox'] = True
            context['bouton_supprimer'] = False
            context['mdp_longueur_min'] = utils_transfert_familles.MDP_LONGUEUR_MIN
            context['boutons_liste'] = list(context['boutons_liste']) + [
                {"label": "Exporter la sélection", "classe": "btn btn-default", "href": "#", "onclick": "ouvrir_export_familles(); return false;", "icone": "fa fa-download"},
                {"label": "Importer", "classe": "btn btn-default", "href": reverse_lazy("familles_importer"), "icone": "fa fa-upload"},
            ]
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:pk", "idfamille"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        rue_resid = columns.TextColumn("Rue", processor='Get_rue_resid')
        cp_resid = columns.TextColumn("CP", processor='Get_cp_resid')
        ville_resid = columns.TextColumn("Ville",  sources=None, processor='Get_ville_resid')
        secteur = columns.TextColumn("Secteur", sources=None, processor='Get_secteur')
        mail = columns.TextColumn("Email", processor="Get_mail")
        portable = columns.TextColumn("Portable", processor="Get_portable")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idfamille", "nom", "rue_resid", "cp_resid", "ville_resid", "mail", "portable", "secteur", "date_creation"]
            hidden_columns = ["secteur", "date_creation"]
            processors = {
                "date_creation": helpers.format_date("%d/%m/%Y %H:%M"),
            }
            ordering = ["nom"]

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.pk])),
            ]
            return self.Create_boutons_actions(html)

        def Get_rue_resid(self, instance, *args, **kwargs):
            return instance.rue_resid

        def Get_cp_resid(self, instance, *args, **kwargs):
            return instance.cp_resid

        def Get_ville_resid(self, instance, *args, **kwargs):
            return instance.ville_resid

        def Get_secteur(self, instance, *args, **kwargs):
            return instance.secteur

        def Get_mail(self, instance, *args, **kwargs):
            return instance.mail

        def Get_portable(self, instance, *args, **kwargs):
            return instance.mobile


    class datatable_class_transfert(datatable_class):
        """ Liste avec cases à cocher pour l'export de fiches familles """
        check = columns.CheckBoxSelectColumn(label="")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idfamille", "nom", "rue_resid", "cp_resid", "ville_resid", "mail", "portable", "secteur", "date_creation"]
            hidden_columns = ["secteur", "date_creation"]
            processors = {
                "date_creation": helpers.format_date("%d/%m/%Y %H:%M"),
            }
            ordering = ["nom"]


class Supprimer_famille(Page, crud.Supprimer):
    form_class = Formulaire

    def get_object(self):
        return Famille.objects.get(pk=self.kwargs['idfamille'])




class Onglet(CustomView):
    menu_code = "individus_toc"
    objet_singulier = "une famille"
    liste_onglets = LISTE_ONGLETS

    def get_context_data(self, **kwargs):
        context = super(Onglet, self).get_context_data(**kwargs)
        context['page_titre'] = "Fiche famille"
        context['liste_onglets'] = [dict_onglet for dict_onglet in self.liste_onglets if self.request.user.has_perm("core.famille_%s" % dict_onglet["code"])]
        context['famille'] = Famille.objects.get(pk=self.kwargs['idfamille'])
        context['idfamille'] = self.kwargs['idfamille']
        context['categories'] = CATEGORIES_RATTACHEMENT
        context['rattachements'] = Rattachement.objects.prefetch_related('individu').filter(famille_id=self.kwargs['idfamille']).order_by("individu__pk")
        context['categories_utilisees'] = self.Get_categories_utilisees(context['rattachements'])
        return context

    def Get_categories_utilisees(self, rattachements=[]):
        liste_categories = []
        for rattachement in rattachements:
            categorie = CATEGORIES_RATTACHEMENT[rattachement.categorie-1]
            if categorie not in liste_categories:
                liste_categories.append(categorie)
        liste_categories.sort()
        return liste_categories

    def Get_idfamille(self):
        return self.kwargs.get('idfamille', None)



class Resume(Onglet, DetailView):
    template_name = "fiche_famille/famille_resume.html"

    def get_context_data(self, **kwargs):
        context = super(Resume, self).get_context_data(**kwargs)
        idfamille = self.kwargs['idfamille']
        context['box_titre'] = "titre ici"
        context['page_titre'] = "Fiche famille"
        context['box_introduction'] = ""
        context['onglet_actif'] = "resume"
        context['nbre_messages_non_lus'] = PortailMessage.objects.filter(famille=context['famille'], utilisateur__isnull=False, date_lecture__isnull=True).count()

        # Alertes
        context['pieces_fournir'] = utils_pieces_manquantes.Get_pieces_manquantes(famille=context['famille'], only_invalides=True, utilisateur=self.request.user)
        context['cotisations_manquantes'] = utils_cotisations_manquantes.Get_cotisations_manquantes(famille=context['famille'])
        context['informations_manquantes'] = utils_informations_manquantes.Get_informations_manquantes(famille=context['famille'])
        context['vaccinations_manquantes'] = utils_vaccinations.Get_vaccins_manquants_famille(famille=context['famille'])
        context['assurances_manquantes'] = utils_assurances.Get_assurances_manquantes_famille(famille=context['famille'])
        context['nbre_alertes'] = len(context['pieces_fournir']) + len(context['cotisations_manquantes']) + len(context['informations_manquantes']) + len(context['vaccinations_manquantes']) + len(context['assurances_manquantes'])

        # Notes
        conditions = (Q(utilisateur=self.request.user) | Q(utilisateur__isnull=True)) & (Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True))
        context['notes'] = Note.objects.filter(conditions, famille_id=idfamille).order_by("date_saisie")

        # Recherche les notes qui doivent affichées dans le popup à l'ouverture de la fiche famille
        key_note_rappel = "notes_rappel_famille_%d" % idfamille
        context["notes_rappel_famille"] = [note for note in context["notes"] if note.rappel_famille]
        if context["notes_rappel_famille"]:
            if cache.get(key_note_rappel, False):
                context["notes_rappel_famille"] = []
            else:
                cache.set(key_note_rappel, True, timeout=10*60*60)

        # Calcul du solde global
        total_prestations = Prestation.objects.values('famille_id').filter(famille_id=idfamille).aggregate(total=Sum("montant"))
        total_reglements = Reglement.objects.values('famille_id').filter(famille_id=idfamille).aggregate(total=Sum("montant"))
        total_du = total_prestations["total"] if total_prestations["total"] else Decimal(0)
        total_regle = total_reglements["total"] if total_reglements["total"] else Decimal(0)
        context["solde_global"] = total_regle - total_du

        # Détail du solde global par activité (les règlements sont rattachés aux activités via la ventilation)
        # Les prestations sans activité sont regroupées par catégorie : adhésions, locations et autres prestations
        complements = {"cotisation": "Adhésions", "location": "Locations"}
        def Get_ligne(idactivite, nom_activite, categorie):
            if idactivite:
                return dict_soldes.setdefault(idactivite, {"nom": nom_activite, "solde": Decimal(0)})
            nom = complements.get(categorie, "Autres prestations")
            return dict_soldes.setdefault(nom, {"nom": nom, "solde": Decimal(0), "complement": True})

        dict_soldes = {}
        for ligne in Prestation.objects.filter(famille_id=idfamille).values("activite_id", "activite__nom", "categorie").annotate(total=Sum("montant")).order_by():
            Get_ligne(ligne["activite_id"], ligne["activite__nom"], ligne["categorie"])["solde"] -= ligne["total"] or Decimal(0)
        total_ventile = Decimal(0)
        for ligne in Ventilation.objects.filter(famille_id=idfamille).values("prestation__activite_id", "prestation__activite__nom", "prestation__categorie").annotate(total=Sum("montant")).order_by():
            Get_ligne(ligne["prestation__activite_id"], ligne["prestation__activite__nom"], ligne["prestation__categorie"])["solde"] += ligne["total"] or Decimal(0)
            total_ventile += ligne["total"] or Decimal(0)

        # Période concernée : dates de la première et de la dernière prestation non soldée
        ventilation_prestation = Ventilation.objects.filter(prestation=OuterRef("pk")).values("prestation").annotate(total=Sum("montant")).values("total")
        prestations_non_soldees = Prestation.objects.filter(famille_id=idfamille).annotate(
            ecart=ExpressionWrapper(F("montant") - Coalesce(Subquery(ventilation_prestation, output_field=DecimalField()), Decimal(0), output_field=DecimalField()), output_field=DecimalField()))
        prestations_non_soldees = prestations_non_soldees.filter(Q(ecart__gt=Decimal("0.005")) | Q(ecart__lt=Decimal("-0.005")))  # Tolérance pour les bases qui somment en virgule flottante
        for ligne in prestations_non_soldees.values("activite_id", "activite__nom", "categorie").annotate(date_min=Min("date"), date_max=Max("date")).order_by():
            valeurs = Get_ligne(ligne["activite_id"], ligne["activite__nom"], ligne["categorie"])
            valeurs["periode_debut"] = min(valeurs.get("periode_debut", ligne["date_min"]), ligne["date_min"])
            valeurs["periode_fin"] = max(valeurs.get("periode_fin", ligne["date_max"]), ligne["date_max"])

        lignes = [valeurs for valeurs in dict_soldes.values() if valeurs["solde"]]
        soldes_activites = sorted([valeurs for valeurs in lignes if not valeurs.get("complement")], key=lambda x: x["nom"])
        soldes_activites += [valeurs for nom in ("Adhésions", "Locations", "Autres prestations") for valeurs in lignes if valeurs.get("complement") and valeurs["nom"] == nom]
        if total_regle - total_ventile:
            soldes_activites.append({"nom": "Règlements non ventilés", "solde": total_regle - total_ventile, "complement": True})
        context["soldes_activites"] = soldes_activites

        # Calcul du solde facturé
        factures_impayees = Facture.objects.select_related("prefixe").filter(famille_id=idfamille, etat__isnull=True).exclude(solde_actuel=0).order_by("date_edition", "numero")
        context["factures_impayees"] = factures_impayees
        context["solde_facture"] = -sum([facture.solde_actuel for facture in factures_impayees], Decimal(0))

        # Inscriptions actuelles
        conditions = Q(famille_id=idfamille) & Q(date_debut__lte=datetime.date.today()) & (Q(date_fin__isnull=True) | Q(date_fin__gte=datetime.date.today()))
        conditions &= (Q(activite__date_fin__isnull=True) | Q(activite__date_fin__gte=datetime.date.today()))
        dict_inscriptions_actuelles = {}
        for inscription in Inscription.objects.select_related("activite", "groupe", "categorie_tarif").filter(conditions).order_by("date_debut"):
            dict_inscriptions_actuelles.setdefault(inscription.individu_id, [])
            if inscription.activite.nom not in dict_inscriptions_actuelles[inscription.individu_id]:
                dict_inscriptions_actuelles[inscription.individu_id].append("%s (%s - %s)\n" % (inscription.activite.nom, inscription.groupe.nom, inscription.categorie_tarif.nom))
        context["inscriptions_actuelles"] = dict_inscriptions_actuelles

        return context

    def get_object(self):
        return Famille.objects.get(pk=self.kwargs['idfamille'])
