# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse, HttpResponseRedirect
from django.template import Template, RequestContext
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Attestation, Prestation
from core.utils import utils_dates, utils_texte, utils_preferences
from core.data import data_modeles_emails
from fiche_famille.forms.famille_attestations import Formulaire as Form_parametres
from fiche_famille.forms.famille_attestations import Formulaire_prestations
from fiche_famille.views.famille import Onglet
from facturation.utils import utils_facturation, utils_impression_facture


def Get_donnees(request):
    # Récupération des données
    form_parametres = Form_parametres(request.POST, idfamille=int(request.POST.get("famille")), utilisateur=request.user, request=request)
    if not form_parametres.is_valid():
        liste_erreurs = form_parametres.errors.as_data().keys()
        return JsonResponse({"erreur": "Veuillez renseigner les champs manquants : %s." % ", ".join(liste_erreurs)}, status=401)
    parametres = form_parametres.cleaned_data
    prestations_defaut = request.POST.get("prestations_defaut", "")

    # Création et rendu du formulaire contenant uniquement le widget Prestations
    date_debut, date_fin = utils_dates.ConvertDateRangePicker(parametres["periode"])
    conditions = Q(date__gte=date_debut, date__lte=date_fin, famille=parametres["famille"])
    prestations = Prestation.objects.select_related("individu", "activite").filter(conditions).order_by("individu__prenom", "activite__nom", "label")
    html = "{% load crispy_forms_tags %} {{ form.prestations|as_crispy_field }}"
    html_widget_prestations = Template(html).render(RequestContext(request, {"form": Formulaire_prestations(prestations=prestations, selections=prestations_defaut)}))

    return JsonResponse({"html_widget_prestations": html_widget_prestations})


def Impression_pdf(request):
    # Récupération des données
    form_parametres = Form_parametres(request.POST, idfamille=int(request.POST.get("famille")), utilisateur=request.user, request=request)
    if not form_parametres.is_valid():
        liste_erreurs = form_parametres.errors.as_data().keys()
        return JsonResponse({"erreur": "Veuillez renseigner les champs manquants : %s." % ", ".join(liste_erreurs)}, status=401)
    parametres = form_parametres.cleaned_data

    # Validation des données
    if not parametres["date_edition"]: return JsonResponse({"erreur": "Vous devez saisir une date d'édition"}, status=401)
    if not parametres["numero"]: return JsonResponse({"erreur": "Vous devez saisir un numéro de reçu"}, status=401)
    if not parametres["modele"]: return JsonResponse({"erreur": "Vous devez sélectionner un modèle de document"}, status=401)
    if not parametres["prestations"]: return JsonResponse({"erreur": "Vous devez cocher au moins une prestation à inclure"}, status=401)

    IDfamille = parametres["famille"].pk
    date_debut, date_fin = utils_dates.ConvertDateRangePicker(parametres["periode"])

    # Recherche les individus, activités et noms de prestations à inclure
    individus, activites = [], []
    liste_conditions = Q()
    for prestation in Prestation.objects.filter(pk__in=[int(idprestation) for idprestation in parametres["prestations"].split(";")]):
        # Individus à inclure
        idindividu = prestation.individu_id if prestation.individu_id else 0
        if idindividu not in individus: individus.append(idindividu)
        # Activités à inclure
        idactivite = prestation.activite_id if prestation.activite_id else None
        if idactivite not in activites: activites.append(idactivite)
        # Labels de prestation à inclure
        liste_conditions |= Q(individu=prestation.individu, activite=prestation.activite, label=prestation.label)

    # Recherche des données de facturation
    facturation = utils_facturation.Facturation()
    dict_attestations = facturation.GetDonnees(liste_activites=activites, date_debut=date_debut, date_fin=date_fin, mode="attestation", IDfamille=IDfamille,
                                               liste_IDindividus=individus, liste_conditions=liste_conditions)

    # Si aucune attestation trouvée
    if not dict_attestations:
        return JsonResponse({"erreur": "Aucune donnée n'a été trouvée pour les paramètres donnés"}, status=401)

    # Rajoute les données du formulaire
    dict_attestations[IDfamille].update({
        "{DATE_EDITION}": parametres["date_edition"],
        "{SIGNATAIRE}": parametres["signataire"],
        "{NUM_ATTESTATION}": parametres["numero"],
    })

    # Fusion du texte d'introduction
    dict_options = parametres["options_impression"]
    dict_attestations[IDfamille]["texte_introduction"] = utils_texte.Fusionner_motscles(dict_options["texte_introduction"], dict_attestations[IDfamille])

    # Renvoie les infos au template pour la sauvegarde
    infos = {
        "total": float(dict_attestations[IDfamille]["total"]),
        "regle": float(dict_attestations[IDfamille]["ventilation"]),
        "solde": float(dict_attestations[IDfamille]["solde"]),
    }

    # Création du PDF
    impression = utils_impression_facture.Impression(dict_donnees=dict_attestations, dict_options=dict_options, IDmodele=parametres["modele"].pk, mode="attestation")
    nom_fichier = impression.Get_nom_fichier()

    # Récupération des valeurs de fusion
    champs = {motcle: dict_attestations[IDfamille].get(motcle, "") for motcle, label in data_modeles_emails.Get_mots_cles("attestation_presence")}
    return JsonResponse({"infos": infos, "nom_fichier": nom_fichier, "categorie": "attestation_presence", "label_fichier": "Attestation de présence", "champs": champs, "idfamille": IDfamille})


class Page(Onglet):
    model = Attestation
    url_liste = "famille_attestations_liste"
    url_ajouter = "famille_attestations_ajouter"
    url_modifier = "famille_attestations_modifier"
    url_supprimer = "famille_attestations_supprimer"
    description_liste = "Vous pouvez créer ici des attestations de présence."
    description_saisie = "Saisissez toutes les informations concernant l'attestation et cliquez sur Aperçu PDF ou Envoyer par email. Vous pourrez ensuite mémoriser l'attestation en cliquant sur le bouton Enregistrer."
    objet_singulier = "une attestation de présence"
    objet_pluriel = "des attestations de présence"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Attestations de présence"
        context['onglet_actif'] = "outils"
        context['boutons_liste'] = [
            {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'idfamille': self.kwargs.get('idfamille', None)}), "icone": "fa fa-plus"},
        ]
        context["url_get_donnees"] = "ajax_attestation_get_donnees"
        context["url_impression_pdf"] = "ajax_attestation_impression_pdf"
        return context

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idfmille au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idfamille"] = self.Get_idfamille()
        form_kwargs["utilisateur"] = self.request.user
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idfamille': self.kwargs.get('idfamille', None)})

    def form_valid(self, form):
        if getattr(self, "verbe_action", None) == "Supprimer":
            return super().form_valid(form)

        # Vérifie que l'attestation a été générée
        if "infos" not in form.cleaned_data:
            messages.add_message(self.request, messages.ERROR, "Vous devez cliquer sur Aperçu ou Envoyer par Email avant d'enregistrer")
            return self.render_to_response(self.get_context_data(form=form))

        # Enregistre l'attestation
        if not self.object and not Attestation.objects.filter(numero=form.cleaned_data["numero"]).exists():
            Attestation.objects.create(numero=form.cleaned_data["numero"], date_edition=form.cleaned_data["date_edition"],
                                     famille=form.cleaned_data["famille"],
                                     date_debut=form.cleaned_data["periode"].split(";")[0], date_fin=form.cleaned_data["periode"].split(";")[1],
                                     total=form.cleaned_data["infos"]["total"], regle=form.cleaned_data["infos"]["regle"],
                                     solde=form.cleaned_data["infos"]["solde"], prestations=form.cleaned_data["prestations"])

        if self.object:
            self.object.numero = form.cleaned_data["numero"]
            self.object.date_edition = form.cleaned_data["date_edition"]
            self.object.date_debut = form.cleaned_data["periode"].split(";")[0]
            self.object.date_fin = form.cleaned_data["periode"].split(";")[1]
            self.object.total = form.cleaned_data["infos"]["total"]
            self.object.regle = form.cleaned_data["infos"]["regle"]
            self.object.solde = form.cleaned_data["infos"]["solde"]
            self.object.famille = form.cleaned_data["famille"]
            self.object.prestations = form.cleaned_data["prestations"]
            self.object.save()

        return HttpResponseRedirect(self.get_success_url())


class Liste(Page, crud.Liste):
    model = Attestation
    template_name = "fiche_famille/famille_pieces.html"

    def get_queryset(self):
        return Attestation.objects.filter(Q(famille=self.Get_idfamille()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ["idattestation", "numero", 'date_edition', 'date_debut', 'date_fin', 'total', 'regle', 'solde']
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        total = columns.TextColumn("Total", sources=['total'], processor='Formate_total')
        regle = columns.TextColumn("Réglé", sources=['regle'], processor='Formate_regle')
        solde = columns.TextColumn("Solde", sources=['solde'], processor='Formate_solde')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idattestation', 'numero', 'date_edition', 'date_debut', 'date_fin', 'total', 'regle', 'solde', 'actions']
            processors = {
                'date_edition': helpers.format_date('%d/%m/%Y'),
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ['date_edition']

        def Formate_total(self, instance, **kwargs):
            return "%0.2f %s" % (instance.total, utils_preferences.Get_symbole_monnaie())

        def Formate_regle(self, instance, **kwargs):
            return "%0.2f %s" % (instance.regle, utils_preferences.Get_symbole_monnaie())

        def Formate_solde(self, instance, **kwargs):
            return "%0.2f %s" % (instance.solde, utils_preferences.Get_symbole_monnaie())

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idactivite dans les boutons d'actions """
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.famille.idfamille, instance.pk])),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.famille.idfamille, instance.pk])),
            ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Form_parametres
    template_name = "fiche_famille/famille_devis.html"


class Modifier(Page, crud.Modifier):
    form_class = Form_parametres
    template_name = "fiche_famille/famille_devis.html"


class Supprimer(Page, crud.Supprimer):
    template_name = "fiche_famille/famille_delete.html"
