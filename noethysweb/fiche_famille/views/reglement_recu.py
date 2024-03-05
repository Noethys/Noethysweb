# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.db.models import Sum, Q
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Recu, Reglement, Ventilation, ModeleImpression
from core.utils import utils_texte, utils_preferences, utils_questionnaires, utils_infos_individus, utils_dates
from core.data import data_modeles_emails
from fiche_famille.forms.reglement_recu import Formulaire
from fiche_famille.views.famille import Onglet


def Generer_recu(donnees={}):
    # Importation des données
    reglement = Reglement.objects.get(pk=donnees["idreglement"])
    infos_famille = reglement.famille.Get_infos()

    # Importation du modèle d'impression
    if donnees.get("idmodele_impression", None):
        modele_impression = ModeleImpression.objects.get(pk=donnees["idmodele_impression"])
        donnees["idmodele"] = modele_impression.modele_document_id
        donnees.update(json.loads(modele_impression.options))

    # Préparation des valeurs de fusion
    dict_donnees = {
        "{IDFAMILLE}": str(reglement.famille_id),
        "{FAMILLE}": infos_famille["nom"],
        "{DATE_EDITION}": utils_dates.ConvertDateToFR(donnees["date_edition"]),
        "{SIGNATAIRE}": donnees["signataire"],
        "{DESTINATAIRE_NOM}": infos_famille["nom"],
        "{DESTINATAIRE_RUE}": infos_famille["rue"],
        "{DESTINATAIRE_VILLE}": "%s %s" % (infos_famille["cp"] or "", infos_famille["ville"] or ""),
        "{NUM_RECU}": donnees["numero"],
        "{IDREGLEMENT}": str(reglement.pk),
        "{DATE_REGLEMENT}": utils_dates.ConvertDateToFR(reglement.date) if reglement.date else "",
        "{MODE_REGLEMENT}": reglement.mode.label,
        "{NOM_EMETTEUR}": reglement.emetteur.nom if reglement.emetteur else "",
        "{NUM_PIECE}": reglement.numero_piece,
        "{MONTANT_REGLEMENT}": float(reglement.montant),
        "{MONTANT}": "%0.2f %s" % (reglement.montant, utils_preferences.Get_symbole_monnaie()),
        "{NOM_PAYEUR}": reglement.payeur.nom,
        "{NUM_QUITTANCIER}": reglement.numero_quittancier,
        "{DATE_SAISIE}": utils_dates.ConvertDateToFR(reglement.date_saisie),
        "{DATE_DIFFERE}": utils_dates.ConvertDateToFR(reglement.date_differe) if reglement.date_differe else "",
        "{OBSERVATIONS}": reglement.observations,
        "prestations": [],
        }

    if donnees["afficher_prestations"]:
        prestations = Ventilation.objects.values('prestation', 'prestation__date', 'prestation__label', 'prestation__activite__nom', 'prestation__individu__nom', 'prestation__individu__prenom').filter(reglement_id=donnees["idreglement"]).annotate(total=Sum("montant"))
        dict_donnees["prestations"] = prestations

    # Récupération des infos de base individus et familles
    infosIndividus = utils_infos_individus.Informations(liste_familles=[donnees["idfamille"],])
    dict_donnees.update(infosIndividus.GetDictValeurs(mode="famille", ID=reglement.famille_id, formatChamp=True))

    # Récupération des questionnaires
    questionnaires = utils_questionnaires.ChampsEtReponses(categorie="famille")
    for dictReponse in questionnaires.GetDonnees(reglement.famille_id):
        dict_donnees[dictReponse["champ"]] = dictReponse["reponse"]
        if dictReponse["controle"] == "codebarres":
            dict_donnees["{CODEBARRES_QUESTION_%d}" % dictReponse["IDquestion"]] = dictReponse["reponse"]

    # Fusion des mots-clés dans le texte d'introduction
    dict_donnees["intro"] = utils_texte.Fusionner_motscles(donnees["intro"], dict_donnees)

    # Création du PDF
    from fiche_famille.utils import utils_impression_recu
    impression = utils_impression_recu.Impression(titre="Reçu de règlement", dict_donnees=dict_donnees, IDmodele=int(donnees["idmodele"]))
    nom_fichier = impression.Get_nom_fichier()

    # Récupération des valeurs de fusion
    champs = {motcle: dict_donnees.get(motcle, "") for motcle, label in data_modeles_emails.Get_mots_cles("recu_reglement")}
    return {"nom_fichier": nom_fichier, "categorie": "recu_reglement", "label_fichier": "Reçu de règlement", "champs": champs, "idfamille": donnees["idfamille"]}


def Impression_pdf(request):
    # Récupération des données du formulaire
    idmodele_impression = int(request.POST.get("idmodele_impression"))
    date_edition = request.POST.get("date_edition")
    numero = request.POST.get("numero")
    idreglement = int(request.POST.get("idreglement"))
    idmodele = request.POST.get("modele")
    idfamille = int(request.POST.get("idfamille"))
    signataire = request.POST.get("signataire")
    intro = request.POST.get("intro")
    afficher_prestations = request.POST.get("afficher_prestations") == 'true'

    # Validation des données
    if not idmodele: return JsonResponse({"erreur": "Vous devez sélectionner un modèle de document"}, status=401)
    if not numero: return JsonResponse({"erreur": "Vous devez saisir un numéro de reçu"}, status=401)
    if not date_edition: return JsonResponse({"erreur": "Vous devez saisir une date d'édition"}, status=401)

    # Génération du reçu
    resultat = Generer_recu(donnees={"idmodele_impression": idmodele_impression, "idreglement": idreglement, "date_edition": date_edition, "numero": numero, "idmodele": idmodele, "idfamille": idfamille,
                                      "signataire": signataire, "intro": intro, "afficher_prestations": afficher_prestations})
    return JsonResponse(resultat)


class Page(Onglet):
    model = Recu
    url_liste = "famille_recus_liste"
    url_ajouter = None
    url_modifier = "famille_recus_modifier"
    url_supprimer = "famille_recus_supprimer"
    description_liste = "Retrouvez ici la liste des reçus de règlements édités."
    description_saisie = "Renseignez les champs demandés et cliquez sur le bouton Enregistrer."
    objet_singulier = "un reçu"
    objet_pluriel = "des reçus"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Reçus"
        context['onglet_actif'] = "reglements"
        return context

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idfmille au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idfamille"] = self.Get_idfamille()
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idfamille': self.kwargs.get('idfamille', None)})


class Liste(Page, crud.Liste):
    model = Recu
    template_name = "fiche_famille/famille_liste.html"

    def get_queryset(self):
        return Recu.objects.filter(Q(famille=self.Get_idfamille()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ['idrecu', 'numero', 'date_edition']
        utilisateur = columns.TextColumn("Utilisateur", sources=None, processor='Formate_utilisateur')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idrecu', 'numero', 'date_edition', 'utilisateur', 'actions']
            processors = {
                'date_edition': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ['date_edition']

        def Formate_utilisateur(self, instance, **kwargs):
            if instance.utilisateur:
                return instance.utilisateur.get_full_name() or instance.utilisateur.get_short_name() or instance.utilisateur
            return ""

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idactivite dans les boutons d'actions """
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.famille.idfamille, instance.pk])),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.famille.idfamille, instance.pk])),
            ]
            return self.Create_boutons_actions(html)


class Ajouter(Onglet, crud.Ajouter):
    form_class = Formulaire
    template_name = "fiche_famille/famille_edit.html"
    objet_singulier = ""
    objet_pluriel = ""
    description_saisie = ""
    titre_historique = "Ajouter un reçu de règlement"

    def Get_detail_historique(self, instance):
        return "Famille=%s, Règlement=ID%s" % (instance.famille, instance.pk)

    def get_context_data(self, **kwargs):
        context = super(Ajouter, self).get_context_data(**kwargs)
        context['box_titre'] = "Créer un reçu de règlement"
        context['box_introduction'] = "Renseignez les paramètres et cliquez sur Aperçu PDF. Terminez en cliquant sur le bouton Enregistrer pour mémoriser le reçu."
        context['onglet_actif'] = "reglements"
        return context

    def get_success_url(self):
        return reverse_lazy("famille_reglements_liste", kwargs={'idfamille': self.kwargs.get('idfamille', None)})

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idindividu au formulaire """
        form_kwargs = super(Ajouter, self).get_form_kwargs(**kwargs)
        form_kwargs["idfamille"] = self.kwargs["idfamille"]
        form_kwargs["idreglement"] = self.kwargs["idreglement"]
        form_kwargs["utilisateur"] = self.request.user
        return form_kwargs


class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "fiche_famille/famille_edit.html"


class Supprimer(Page, crud.Supprimer):
    template_name = "fiche_famille/famille_delete.html"

