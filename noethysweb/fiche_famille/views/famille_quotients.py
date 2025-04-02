# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Min, Max
from django.http import JsonResponse
from django.core.cache import cache
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Quotient, Prestation
from fiche_famille.forms.famille_quotients import Formulaire
from fiche_famille.views.famille import Onglet
from individus.utils import utils_api_particulier


def Check_mdp_api_particulier(request):
    """ Vérifie si le mot de passe de l'API Particulier de l'utilisateur est mémorisé """
    if cache.get("mdp_api_particulier_user%d" % request.user.pk):
        return JsonResponse({"resultat": "ok"})
    if not request.user.token_api_particulier:
        return JsonResponse({"erreur": "no_token"}, status=401)
    return JsonResponse({"erreur": "no_mdp"}, status=401)


def Memoriser_mdp_api_particulier(request):
    """ Mémorise le mot de passe de l'API Particulier de l'utilisateur """
    mdp = request.POST.get("mdp_api_particulier")
    if not mdp or len(mdp) != 5:
        return JsonResponse({"erreur": "Ce mot de passe doit comporter 5 caractères"}, status=401)

    # Vérifie validité auprès de l'API
    if not utils_api_particulier.Check_token(request.user.token_api_particulier + mdp):
        return JsonResponse({"erreur": "Ce mot de passe n'est pas valide"}, status=401)

    # Mémorise le mdp dans le cache
    cache.set("mdp_api_particulier_user%d" % request.user.pk, mdp, timeout=43200)
    return JsonResponse({"resultat": "ok"})


def Appel_api_particulier(request):
    """ Consulter l'API Particulier """
    # Initialisation du module API
    api = utils_api_particulier.Api_particulier(request=request)
    if api.erreurs_generales:
        return JsonResponse({"html": api.Get_html_erreurs(idfamille=int(request.POST.get("idfamille")))})

    # Consultation pour la famille
    resultat = api.Consulter_famille(famille=int(request.POST.get("idfamille")))
    if not resultat:
        return JsonResponse({"html": api.Get_html_erreurs(idfamille=int(request.POST.get("idfamille")))})

    return JsonResponse({"html": resultat.Get_html_resultat()})


def Enregistrer_quotient_api_particulier(request):
    """ Enregistrement du quotient trouvé """""
    form = Formulaire(json.loads(request.POST.get("form")), request=request, idfamille=request.POST["idfamille"])
    if not form.is_valid():
        liste_erreurs = ", ".join([erreur[0].message for field, erreur in form.errors.as_data().items()])
        return JsonResponse({"erreur": liste_erreurs}, status=401)

    # Validation et recalcul des prestations si besoins
    resultat, form = Validation_form(form, request=request, idfamille=request.POST["idfamille"], verbe_action="Ajouter")
    if not resultat:
        liste_erreurs = ", ".join([erreur[0].message for field, erreur in form.errors.as_data().items()])
        return JsonResponse({"erreur": liste_erreurs}, status=401)

    return JsonResponse({"succes": True})


class Page(Onglet):
    model = Quotient
    url_liste = "famille_quotients_liste"
    url_ajouter = "famille_quotients_ajouter"
    url_modifier = "famille_quotients_modifier"
    url_supprimer = "famille_quotients_supprimer"
    description_liste = "Consultez et saisissez ici les quotients familiaux de la famille."
    description_saisie = "Saisissez toutes les informations concernant le quotient et cliquez sur le bouton Enregistrer."
    objet_singulier = "un quotient familial"
    objet_pluriel = "des quotients familiaux"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        if not hasattr(self, "verbe_action"):
            context['box_titre'] = "Quotients familiaux"
        context['onglet_actif'] = "quotients"
        if self.request.user.has_perm("core.famille_quotients_modifier"):
            context['boutons_liste'] = [
                {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'idfamille': self.kwargs.get('idfamille', None)}), "icone": "fa fa-plus"},
                {"label": "Importer depuis l'API Particulier", "classe": "btn btn-default", "href": "#", "onclick": "ouvrir_api_particulier();", "icone": "fa fa-plus"},
            ]
        return context

    def test_func_page(self):
        if getattr(self, "verbe_action", None) in ("Ajouter", "Modifier", "Supprimer") and not self.request.user.has_perm("core.famille_quotients_modifier"):
            return False
        return True

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idindividu au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idfamille"] = self.Get_idfamille()
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idfamille': self.kwargs.get('idfamille', None)})


def Validation_form(form=None, request=None, idfamille=None, object=None, verbe_action=None):
    # Vérifie que ce quotient n'est pas en conflit avec un autre quotient existant
    conditions = Q(famille_id=idfamille, type_quotient=form.cleaned_data["type_quotient"], date_debut__lte=form.cleaned_data["date_fin"], date_fin__gte=form.cleaned_data["date_debut"])
    quotients = Quotient.objects.filter(conditions).exclude(pk=object.pk if object else None)
    if quotients:
        form.add_error(None, "Il existe déjà %d quotient(s) de même type sur la même période !" % len(quotients))
        return False, form

    # Vérifie si un recalcul des prestations est nécessaire
    if "date_debut" in form.changed_data or "date_fin" in form.changed_data or "quotient" in form.changed_data or "revenu" in form.changed_data:

        # Période à recalculer
        date_min = min(form.cleaned_data["date_debut"], form.initial["date_debut"]) if "date_debut" in form.initial else form.cleaned_data["date_debut"]
        date_max = max(form.cleaned_data["date_fin"], form.initial["date_fin"]) if "date_fin" in form.initial else form.cleaned_data["date_fin"]

        # Recherche s'il y a des prestations facturées sur cette période
        prestations_facturees = Prestation.objects.filter(famille=form.cleaned_data["famille"], date__range=(date_min, date_max), facture__isnull=False).aggregate(Min("date"), Max("date"))
        if prestations_facturees["date__min"]:
            # Si le montant du QF a été modifié
            if "quotient" in form.changed_data:
                form.add_error(None, "Vous ne pouvez pas modifier le montant du quotient car des prestations sont déjà facturées sur la période du %s au %s. Créez plutôt un nouveau QF." % (prestations_facturees["date__min"].strftime("%d/%m/%Y"), prestations_facturees["date__max"].strftime("%d/%m/%Y")))
                return False, form
            # Si ce sont seulement les dates du QF qui ont été modifiées
            if (form.cleaned_data["date_debut"] > prestations_facturees["date__min"]) or (form.cleaned_data["date_fin"] < prestations_facturees["date__max"]):
                form.add_error(None, "Ces nouvelles dates sont erronées car des prestations sont déjà facturées sur la période du %s au %s. Créez plutôt un nouveau QF." % (prestations_facturees["date__min"].strftime("%d/%m/%Y"), prestations_facturees["date__max"].strftime("%d/%m/%Y")))
                return False, form

        # Enregistrement du quotient
        if verbe_action == "Modifier":
            object.save()
        if verbe_action == "Ajouter":
            object = form.save()

        # Recalcul des prestations
        Recalculer_prestations(request=request, idfamille=idfamille, date_min=date_min, date_max=date_max)

    return True, form


def Recalculer_prestations(request=None, idfamille=None, date_min=None, date_max=None):
    # Recherche s'il y a des prestations à modifier sur la période
    prestations = Prestation.objects.filter(famille_id=idfamille, date__range=(date_min, date_max), facture__isnull=True, activite__isnull=False)
    keys_prestations = list({(prestation.individu_id, prestation.activite_id): True for prestation in prestations}.keys())

    # Recalcule les prestations
    if keys_prestations:
        logger.debug("Recalcul des prestations après changement de QF...")
        from consommations.utils.utils_grille_virtuelle import Grille_virtuelle
        for idindividu, idactivite in keys_prestations:
            grille = Grille_virtuelle(request=request, idfamille=idfamille, idindividu=idindividu, idactivite=idactivite, date_min=date_min, date_max=date_max)
            grille.Recalculer_tout()
            grille.Enregistrer()


class Liste(Page, crud.Liste):
    model = Quotient
    template_name = "fiche_famille/famille_quotients.html"

    def get_queryset(self):
        return Quotient.objects.filter(Q(famille__pk=self.Get_idfamille()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ['idquotient', 'date_debut', 'date_fin', 'type_quotient__nom', 'quotient', 'revenu']

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        type_quotient = columns.TextColumn("Type de quotient", sources=["type_quotient__nom"])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idquotient', 'date_debut', 'date_fin', 'type_quotient', 'quotient', 'revenu']
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ['date_debut']

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idindividu dans les boutons d'actions """
            view = kwargs["view"]
            if not view.request.user.has_perm("core.famille_quotients_modifier"):
                return "<span class='text-red' title='Accès interdit'><i class='fa fa-lock'></i></span>"
            kwargs = view.kwargs
            kwargs["pk"] = instance.pk
            html = [
                self.Create_bouton_modifier(url=reverse(view.url_modifier, kwargs=kwargs)),
                self.Create_bouton_supprimer(url=reverse(view.url_supprimer, kwargs=kwargs)),
            ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "fiche_famille/famille_edit.html"

    def form_valid(self, form):
        resultat, form = Validation_form(form, request=self.request, idfamille=self.Get_idfamille(), object=self.object, verbe_action=self.verbe_action)
        if not resultat:
            return self.render_to_response(self.get_context_data(form=form))
        return super(Ajouter, self).form_valid(form)


class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "fiche_famille/famille_edit.html"

    def form_valid(self, form):
        resultat, form = Validation_form(form, request=self.request, idfamille=self.Get_idfamille(), object=self.object, verbe_action=self.verbe_action)
        if not resultat:
            return self.render_to_response(self.get_context_data(form=form))
        return super(Modifier, self).form_valid(form)


class Supprimer(Page, crud.Supprimer):
    template_name = "fiche_famille/famille_delete.html"

    def Check_protections(self, objet=None):
        protections = []
        prestations_facturees = Prestation.objects.filter(famille=objet.famille, date__range=(objet.date_debut, objet.date_fin), facture__isnull=False).aggregate(Min("date"), Max("date"))
        if prestations_facturees["date__min"]:
            protections.append("Vous ne pouvez pas supprimer ce quotient car des prestations sont déjà facturées sur la période du %s au %s. Créez plutôt un nouveau QF." % (prestations_facturees["date__min"].strftime("%d/%m/%Y"), prestations_facturees["date__max"].strftime("%d/%m/%Y")))
        return protections

    def Apres_suppression(self, objet=None):
        Recalculer_prestations(request=self.request, idfamille=self.Get_idfamille(), date_min=objet.date_debut, date_max=objet.date_fin)
