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
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Attestation
from core.utils import utils_dates, utils_texte, utils_preferences
from core.data import data_modeles_emails
from fiche_famille.forms.famille_attestations import Formulaire as Form_parametres
from fiche_famille.views.famille import Onglet
from facturation.utils import utils_facturation, utils_impression_facture


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

    # Récupération de la période
    date_debut = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[0])
    date_fin = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[1])

    # Recherche des données de facturation
    facturation = utils_facturation.Facturation()
    IDfamille = parametres["famille"].pk
    individus = [int(idindividu) for idindividu in parametres["individus"]]
    activites = [int(idactivite) for idactivite in parametres["activites"]]
    dict_attestations = facturation.GetDonnees(liste_activites=activites, date_debut=date_debut, date_fin=date_fin, mode="attestation", IDfamille=IDfamille,
                                               liste_IDindividus=individus, filtre_prestations=parametres["filtre_prestations"], exclusions_prestations=parametres["exclusions_prestations"])

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
        "individus": ";".join([str(idindividu) for idindividu in dict_attestations[IDfamille]["individus"].keys()]),
        "activites": ";".join([str(idactivite) for idactivite in dict_attestations[IDfamille]["liste_idactivite"]])
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
    description_saisie = "Saisissez toutes les informations concernant l'attestation et cliquez sur le bouton Enregistrer."
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
            Attestation.objects.create(numero=form.cleaned_data["numero"], date_edition=form.cleaned_data["date_edition"], exclusions_prestations=form.cleaned_data["exclusions_prestations"],
                                     activites=form.cleaned_data["infos"]["activites"], filtre_prestations=form.cleaned_data["filtre_prestations"],
                                     individus=form.cleaned_data["infos"]["individus"], famille=form.cleaned_data["famille"],
                                     date_debut=form.cleaned_data["periode"].split(";")[0], date_fin=form.cleaned_data["periode"].split(";")[1],
                                     total=form.cleaned_data["infos"]["total"], regle=form.cleaned_data["infos"]["regle"],
                                     solde=form.cleaned_data["infos"]["solde"])

        if self.object:
            self.object.numero = form.cleaned_data["numero"]
            self.object.date_edition = form.cleaned_data["date_edition"]
            self.object.activites = form.cleaned_data["infos"]["activites"]
            self.object.filtre_prestations = form.cleaned_data["filtre_prestations"]
            self.object.exclusions_prestations = form.cleaned_data["exclusions_prestations"]
            self.object.individus = form.cleaned_data["infos"]["individus"]
            self.object.date_debut = form.cleaned_data["periode"].split(";")[0]
            self.object.date_fin = form.cleaned_data["periode"].split(";")[1]
            self.object.total = form.cleaned_data["infos"]["total"]
            self.object.regle = form.cleaned_data["infos"]["regle"]
            self.object.solde = form.cleaned_data["infos"]["solde"]
            self.object.famille = form.cleaned_data["famille"]
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
    template_name = "fiche_famille/famille_edit.html"


class Modifier(Page, crud.Modifier):
    form_class = Form_parametres
    template_name = "fiche_famille/famille_edit.html"


class Supprimer(Page, crud.Supprimer):
    template_name = "fiche_famille/famille_delete.html"
