# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Famille, Devis
from fiche_famille.forms.famille_devis import Formulaire as Form_parametres
from fiche_famille.views.famille import Onglet
from django.http import JsonResponse, HttpResponseRedirect
from core.utils import utils_dates, utils_texte, utils_preferences
from facturation.utils import utils_facturation, utils_impression_facture
from django.contrib import messages
from django.db.models import Q
from core.data import data_modeles_emails



def Impression_pdf(request):
    # Récupération des données
    form_parametres = Form_parametres(request.POST, idfamille=int(request.POST.get("famille")), utilisateur=request.user, request=request)
    if form_parametres.is_valid() == False:
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
    categories_prestations = parametres["categories"]
    dict_devis = facturation.GetDonnees(liste_activites=activites, date_debut=date_debut, date_fin=date_fin, mode="devis", IDfamille=IDfamille, liste_IDindividus=individus, categories_prestations=categories_prestations)

    # Si aucun devis trouvé
    if not dict_devis:
        return JsonResponse({"erreur": "Aucune donnée n'a été trouvée pour les paramètres donnés"}, status=401)

    # Rajoute les données du formulaire
    dict_devis[IDfamille].update({
        "{DATE_EDITION}": parametres["date_edition"],
        "{SIGNATAIRE}": parametres["signataire"],
        "{NUM_DEVIS}": parametres["numero"],
    })

    # Fusion du texte d'introduction
    dict_options = parametres["options_impression"]
    dict_devis[IDfamille]["texte_introduction"] = utils_texte.Fusionner_motscles(dict_options["texte_introduction"], dict_devis[IDfamille])

    # Renvoie les infos au template pour la sauvegarde
    infos = {
        "total": float(dict_devis[IDfamille]["total"]),
        "regle": float(dict_devis[IDfamille]["ventilation"]),
        "solde": float(dict_devis[IDfamille]["solde"]),
        "individus": ";".join([str(idindividu) for idindividu in dict_devis[IDfamille]["individus"].keys()]),
        "activites": ";".join([str(idactivite) for idactivite in dict_devis[IDfamille]["liste_idactivite"]])
    }

    # Création du PDF
    impression = utils_impression_facture.Impression(dict_donnees=dict_devis, dict_options=dict_options, IDmodele=parametres["modele"].pk, mode="devis")
    nom_fichier = impression.Get_nom_fichier()

    # Récupération des valeurs de fusion
    champs = {motcle: dict_devis[IDfamille].get(motcle, "") for motcle, label in data_modeles_emails.Get_mots_cles("devis")}
    return JsonResponse({"infos": infos, "nom_fichier": nom_fichier, "categorie": "devis", "label_fichier": "Devis", "champs": champs, "idfamille": IDfamille})



class Page(Onglet):
    model = Devis
    url_liste = "famille_devis_liste"
    url_ajouter = "famille_devis_ajouter"
    url_modifier = "famille_devis_modifier"
    url_supprimer = "famille_devis_supprimer"
    description_liste = "Vous pouvez créer ici des devis."
    description_saisie = "Saisissez toutes les informations concernant le devis et cliquez sur le bouton Enregistrer."
    objet_singulier = "un devis"
    objet_pluriel = "des devis"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Devis"
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

        # Vérifie que le devis a été généré
        if "infos" not in form.cleaned_data:
            messages.add_message(self.request, messages.ERROR, "Vous devez cliquer sur Aperçu ou Envoyer par Email avant d'enregistrer")
            return self.render_to_response(self.get_context_data(form=form))

        # Enregistre le devis
        if not self.object:
            Devis.objects.create(numero=form.cleaned_data["numero"], date_edition=form.cleaned_data["date_edition"],
                                     activites=form.cleaned_data["infos"]["activites"], individus=form.cleaned_data["infos"]["individus"],
                                     date_debut=form.cleaned_data["periode"].split(";")[0], date_fin=form.cleaned_data["periode"].split(";")[1],
                                     total=form.cleaned_data["infos"]["total"], regle=form.cleaned_data["infos"]["regle"],
                                     solde=form.cleaned_data["infos"]["solde"], famille=form.cleaned_data["famille"])
        else:
            self.object.numero = form.cleaned_data["numero"]
            self.object.date_edition = form.cleaned_data["date_edition"]
            self.object.activites = form.cleaned_data["infos"]["activites"]
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
    model = Devis
    template_name = "fiche_famille/famille_pieces.html"

    def get_queryset(self):
        return Devis.objects.filter(Q(famille=self.Get_idfamille()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ['iddevis', 'numero', 'date_edition', 'date_debut', 'date_fin', 'total', 'regle', 'solde']

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        total = columns.TextColumn("Total", sources=['total'], processor='Formate_total')
        regle = columns.TextColumn("Réglé", sources=['regle'], processor='Formate_regle')
        solde = columns.TextColumn("Solde", sources=['solde'], processor='Formate_solde')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['iddevis', 'numero', 'date_edition', 'date_debut', 'date_fin', 'total', 'regle', 'solde', 'actions']
            processors = {
                'date_edition': helpers.format_date('%d/%m/%Y'),
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ['date_edition']

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idactivite dans les boutons d'actions """
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.famille.idfamille, instance.pk])),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.famille.idfamille, instance.pk])),
            ]
            return self.Create_boutons_actions(html)

        def Formate_total(self, instance, **kwargs):
            return "%0.2f %s" % (instance.total, utils_preferences.Get_symbole_monnaie())

        def Formate_regle(self, instance, **kwargs):
            return "%0.2f %s" % (instance.regle, utils_preferences.Get_symbole_monnaie())

        def Formate_solde(self, instance, **kwargs):
            return "%0.2f %s" % (instance.solde, utils_preferences.Get_symbole_monnaie())



class Ajouter(Page, crud.Ajouter):
    form_class = Form_parametres
    template_name = "fiche_famille/famille_edit.html"

class Modifier(Page, crud.Modifier):
    form_class = Form_parametres
    template_name = "fiche_famille/famille_edit.html"

class Supprimer(Page, crud.Supprimer):
    template_name = "fiche_famille/famille_delete.html"

