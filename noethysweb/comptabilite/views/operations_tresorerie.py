# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, decimal, json, datetime
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Sum, DecimalField, Case, When, F
from django.contrib import messages
from django.http import JsonResponse
from django.template.context_processors import csrf
from crispy_forms.utils import render_crispy_form
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import ComptaOperation, CompteBancaire, ComptaVentilation
from core.utils import utils_dates, utils_parametres, utils_texte
from comptabilite.forms.operations_tresorerie import Formulaire
from comptabilite.forms.ventilation_tresorerie import Formulaire as Formulaire_ventilation


def Get_form_ventilation(request):
    action = request.POST.get("action", None)
    index = request.POST.get("index", None)
    type_operation = request.POST.get("type_operation", None)

    initial_data = {}
    if "valeur" in request.POST:
        initial_data = json.loads(request.POST["valeur"])
        initial_data["date_budget"] = utils_dates.ConvertDateENGtoDate(initial_data["date_budget"])
        initial_data["montant"] = decimal.Decimal(initial_data["montant"])
        initial_data["index"] = index

    if action == "ajouter":
        initial_data["date_budget"] = utils_dates.ConvertDateFRtoDate(request.POST.get("date_operation", None))

    # Création et rendu html du formulaire
    if action in ("ajouter", "modifier"):
        form = Formulaire_ventilation(request=request, type=type_operation, initial=initial_data)
        return JsonResponse({"form_html": render_crispy_form(form, context=csrf(request))})

    # Validation du formulaire
    form = Formulaire_ventilation(request.POST, request=request)
    if not form.is_valid():
        messages_erreurs = ["<b>%s</b> : %s " % (field.title(), erreur[0].message) for field, erreur in form.errors.as_data().items()]
        return JsonResponse({"erreur": messages_erreurs}, status=401)

    # Mémorisation de l'analytique saisie
    utils_parametres.Set(nom="analytique", categorie="ventilation_tresorerie", utilisateur=request.user, valeur=form.cleaned_data["analytique"].pk)

    # Transformation en chaîne
    dict_retour = {
        "idventilation": form.cleaned_data["idventilation"],
        "date_budget": str(form.cleaned_data["date_budget"]),
        "analytique": form.cleaned_data["analytique"].pk,
        "categorie": form.cleaned_data["categorie"].pk,
        "montant": str(form.cleaned_data["montant"]),
    }
    return JsonResponse({"valeur": dict_retour, "index": form.cleaned_data["index"]})


class Page(crud.Page):
    model = ComptaOperation
    url_liste = "operations_tresorerie_liste"
    url_modifier = "operations_tresorerie_modifier"
    url_supprimer = "operations_tresorerie_supprimer"
    url_ajouter_debit = "operations_tresorerie_ajouter_debit"
    url_ajouter_credit = "operations_tresorerie_ajouter_credit"
    description_liste = "Voici ci-dessous la liste des opérations de trésorerie."
    description_saisie = "Saisissez toutes les informations concernant l'opération à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une opération de trésorerie"
    objet_pluriel = "des opérations de trésorerie"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        if getattr(self, "type", None) == "debit":
            context["box_titre"] += " au débit"
        if getattr(self, "type", None) == "credit":
            context["box_titre"] += " au crédit"
        context["categorie"] = self.Get_categorie()
        context['label_categorie'] = "Compte"
        context['liste_categories'] = [(item.pk, item.nom) for item in CompteBancaire.objects.filter(Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)).order_by("nom")]
        if context['liste_categories']:
            context['boutons_liste'] = [
                {"label": "Ajouter un débit", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter_debit, kwargs={'categorie': self.Get_categorie()}), "icone": "fa fa-plus"},
                {"label": "Ajouter un crédit", "classe": "btn btn-default", "href": reverse_lazy(self.url_ajouter_credit, kwargs={'categorie': self.Get_categorie()}), "icone": "fa fa-plus"},
                {"label": "Ajouter un virement", "classe": "btn btn-default", "href": reverse_lazy("virements_ajouter"), "icone": "fa fa-plus"}, ]
        else:
            context['box_introduction'] = "Vous pouvez saisir ici des opérations de trésorerie.<br><b>Vous devez avoir enregistré au moins un compte bancaire avant de pouvoir ajouter des opérations !</b>"
        return context

    def test_func_page(self):
        # Vérifie que l'utilisateur a une permission d'accéder à ce compte
        idcompte = self.Get_categorie()
        if idcompte and idcompte not in [compte.pk for compte in CompteBancaire.objects.filter(self.Get_condition_structure())]:
            return False
        return True

    def Get_categorie(self):
        idcompte = self.kwargs.get('categorie', None)
        if idcompte:
            return idcompte
        compte = CompteBancaire.objects.filter(self.Get_condition_structure()).order_by("nom")
        return compte[0].pk if compte else 0

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["categorie"] = self.Get_categorie()
        form_kwargs["type"] = getattr(self, "type", None)
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            if getattr(self, "type", None):
                url = self.url_ajouter_debit
            else:
                url = self.url_ajouter_credit
        return reverse_lazy(url, kwargs={'categorie': self.Get_categorie()})

    def form_valid(self, form):
        if getattr(self, "verbe_action", None) == "Supprimer":
            return super().form_valid(form)
        
        # Récupération de la ventilation
        ventilations = json.loads(form.cleaned_data.get("ventilation", "[]"))

        # Vérifie que la ventilation est égale au montant du règlement
        montant_ventilation = sum([decimal.Decimal(ventilation["montant"]) for ventilation in ventilations])
        if montant_ventilation != form.cleaned_data["montant"]:
            messages.add_message(self.request, messages.ERROR, "La ventilation ne correspond pas au montant de l'opération")
            return self.render_to_response(self.get_context_data(form=form))

        # Sauvegarde
        self.object = form.save()

        # Récupération des ventilations existantes
        ventilations_existantes = list(ComptaVentilation.objects.filter(operation=self.object))

        # Sauvegarde des ventilations
        for ventilation in ventilations:
            idventilation = ventilation["idventilation"] if ventilation["idventilation"] else None
            ComptaVentilation.objects.update_or_create(pk=idventilation, defaults={"operation": self.object,
                "date_budget": utils_dates.ConvertDateENGtoDate(ventilation["date_budget"]), "analytique_id": ventilation["analytique"],
                "categorie_id": ventilation["categorie"], "montant": decimal.Decimal(ventilation["montant"])})

        # Suppression des ventilations supprimées
        for ventilation in ventilations_existantes:
            if ventilation.pk not in [int(v["idventilation"]) for v in ventilations if v["idventilation"]]:
                ventilation.delete()

        return super().form_valid(form)


class Liste(Page, crud.Liste):
    model = ComptaOperation
    template_name = "core/crud/liste_avec_categorie.html"

    def get_queryset(self):
        return ComptaOperation.objects.select_related("tiers", "mode").filter(Q(compte=self.Get_categorie()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True

        # Stats du compte
        stats = CompteBancaire.objects.filter(pk=self.Get_categorie()).aggregate(
            solde_final=Sum(Case(When(comptaoperation__type="credit", then=F("comptaoperation__montant")), output_field=DecimalField(), default=0)) - Sum(Case(When(comptaoperation__type="debit", then=F("comptaoperation__montant")), output_field=DecimalField(), default=0)),
            solde_pointe=Sum(Case(When(comptaoperation__type="credit", comptaoperation__releve__isnull=False, then=F("comptaoperation__montant")), output_field=DecimalField(), default=0)) - Sum(Case(When(comptaoperation__type="debit", comptaoperation__releve__isnull=False, then=F("comptaoperation__montant")), output_field=DecimalField(), default=0)),
            solde_jour=Sum(Case(When(comptaoperation__type="credit", comptaoperation__date__lte=datetime.date.today(), then=F("comptaoperation__montant")), output_field=DecimalField(), default=0)) - Sum(Case(When(comptaoperation__type="debit", comptaoperation__date__lte=datetime.date.today(), then=F("comptaoperation__montant")), output_field=DecimalField(), default=0)),
        )

        context['box_conclusion'] = "<center>Solde du jour : <b>%s</b> &nbsp; &nbsp; Solde pointé : <b>%s</b> &nbsp; &nbsp; Solde final : <b>%s</b></center>" % (
            utils_texte.Formate_montant(stats["solde_jour"]),
            utils_texte.Formate_montant(stats["solde_pointe"]),
            utils_texte.Formate_montant(stats["solde_final"])
        )
        return context

    class datatable_class(MyDatatable):
        filtres = ["idoperation", "type", "date", "libelle", "mode", "releve", "num_piece", "debit", "credit", "montant"]
        tiers = columns.TextColumn("Tiers", sources=["tiers__nom"])
        debit = columns.TextColumn("Débit", sources=["montant"], processor="Get_montant_debit")
        credit = columns.TextColumn("Crédit", sources=["montant"], processor="Get_montant_credit")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idoperation", "date", "libelle", "tiers", "mode", "num_piece", "releve", "debit", "credit", "actions"]
            ordering = ["date"]
            processors = {
                "date": helpers.format_date('%d/%m/%Y'),
            }
            labels = {
                "mode": "Mode",
                "num_piece": "N° Pièce",
                "releve": "Relevé",
            }

        def Get_montant_debit(self, instance, **kwargs):
            if instance.type == "debit":
                return "%0.2f" % instance.montant
            return None

        def Get_montant_credit(self, instance, **kwargs):
            if instance.type == "credit":
                return "%0.2f" % instance.montant
            return None

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut la catégorie dans les boutons d'actions """
            if instance.virement:
                html = [
                    self.Create_bouton_modifier(url=reverse("virements_modifier", args=[instance.virement_id])),
                    self.Create_bouton_supprimer(url=reverse("virements_supprimer", args=[instance.virement_id])),
                ]
            else:
                html = [
                    self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.compte_id, instance.pk])),
                    self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.compte_id, instance.pk])),
                ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    type = "debit"


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    pass
