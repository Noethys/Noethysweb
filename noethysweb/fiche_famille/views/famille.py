# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from decimal import Decimal
from django.urls import reverse_lazy, reverse
from django.db.models import Sum, Q
from django.http import JsonResponse
from django.contrib import messages
from django.views.generic.detail import DetailView
from core.views.base import CustomView
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Famille, Note, Rattachement, CATEGORIES_RATTACHEMENT, Prestation, Reglement, PortailMessage, Inscription
from core.utils import utils_texte
from individus.utils import utils_pieces_manquantes
from fiche_individu.forms.individu import Formulaire
from fiche_famille.utils.utils_famille import LISTE_ONGLETS
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

    def get_queryset(self):
        return Famille.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ["fpresent:pk", "fscolarise:pk", "idfamille", "nom", "rue_resid", "cp_resid", "ville_resid"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        rue_resid = columns.TextColumn("Rue", processor='Get_rue_resid')
        cp_resid = columns.TextColumn("CP", processor='Get_cp_resid')
        ville_resid = columns.TextColumn("Ville",  sources=None, processor='Get_ville_resid')
        secteur = columns.TextColumn("Secteur", sources=None, processor='Get_secteur')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idfamille", "nom", "rue_resid", "cp_resid", "ville_resid", "secteur"]
            hidden_columns = ["secteur",]
            processors = {
                'date_creation': helpers.format_date('%d/%m/%Y'),
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
        context['rattachements'] = Rattachement.objects.prefetch_related('individu').filter(famille_id=self.kwargs['idfamille']).order_by("individu__civilite")
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
        context['nbre_alertes'] = len(context['pieces_fournir']) + len(context['cotisations_manquantes'])

        # Notes
        conditions = (Q(utilisateur=self.request.user) | Q(utilisateur__isnull=True)) & (Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True))
        context['notes'] = Note.objects.filter(conditions, famille_id=idfamille).order_by("date_saisie")

        # Calcul du solde
        total_prestations = Prestation.objects.values('famille_id').filter(famille_id=idfamille).aggregate(total=Sum("montant"))
        total_reglements = Reglement.objects.values('famille_id').filter(famille_id=idfamille).aggregate(total=Sum("montant"))
        total_du = total_prestations["total"] if total_prestations["total"] else Decimal(0)
        total_regle = total_reglements["total"] if total_reglements["total"] else Decimal(0)
        context['solde'] = total_du - total_regle

        # Inscriptions actuelles
        conditions = Q(famille_id=idfamille) & Q(date_debut__lte=datetime.date.today()) & (Q(date_fin__isnull=True) | Q(date_fin__gte=datetime.date.today()))
        conditions &= (Q(activite__date_fin__isnull=True) | Q(activite__date_fin__gte=datetime.date.today()))
        dict_inscriptions_actuelles = {}
        for inscription in Inscription.objects.select_related("activite", "groupe").filter(conditions).order_by("date_debut"):
            dict_inscriptions_actuelles.setdefault(inscription.individu_id, [])
            if inscription.activite.nom not in dict_inscriptions_actuelles[inscription.individu_id]:
                dict_inscriptions_actuelles[inscription.individu_id].append("%s (%s)\n" % (inscription.activite.nom, inscription.groupe.nom))
        context["inscriptions_actuelles"] = dict_inscriptions_actuelles

        return context

    def get_object(self):
        return Famille.objects.get(pk=self.kwargs['idfamille'])
