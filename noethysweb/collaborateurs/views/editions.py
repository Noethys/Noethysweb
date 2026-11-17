# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Editions du module Collaborateurs.
    Chaque édition est décrite par une classe (titre, formulaire d'options, lignes proposées à la sélection, génération du PDF ou du fichier Excel).
    Les pages partagent le même gabarit : paramètres à gauche, liste à cocher à droite, boutons d'action en haut. """

import json, logging
logger = logging.getLogger(__name__)
from django.http import JsonResponse, Http404
from django.views.generic import TemplateView
from core.views.base import CustomView
from core.models import DemandeAbsenceCollaborateur
from core.utils import utils_dates
from collaborateurs.forms import editions as formulaires
from collaborateurs.utils import utils_editions, utils_conges


class Edition():
    code = ""                       # Code du menu (et de la permission)
    titre = ""
    introduction = ""
    Formulaire = formulaires.Formulaire_base
    entetes = ["Collaborateur", "Poste", "Groupes", "Contrat"]
    exports = ("pdf",)              # pdf et/ou xlsx
    libelle_lignes = "collaborateur"

    def Get_objets(self, user=None, parametres={}, ids=None):
        return utils_editions.Get_collaborateurs(user, parametres.get("situation", "en_poste"), parametres.get("groupes"), ids=ids)

    def Get_lignes(self, user=None, parametres={}):
        return utils_editions.Lignes_selection_collaborateurs(self.Get_objets(user, parametres))

    def Imprimer(self, objets=[], parametres={}, request=None):
        raise NotImplementedError

    def Exporter_xlsx(self, objets=[], parametres={}, request=None):
        raise NotImplementedError


# ------------------------------------------------- Dossiers et listes -------------------------------------------------

class Edition_fiches(Edition):
    code = "fiches_collaborateurs"
    titre = "Fiches des collaborateurs"
    introduction = "Imprimez une fiche récapitulative par collaborateur : identité, coordonnées, groupes, qualifications, contrats, pièces et questionnaire. Pratique pour constituer les dossiers du personnel."
    Formulaire = formulaires.Formulaire_fiches

    def Imprimer(self, objets=[], parametres={}, request=None):
        from collaborateurs.utils import utils_editions_dossiers
        return utils_editions_dossiers.Impression_fiches(titre=self.titre, dict_donnees={"collaborateurs": objets, "parametres": parametres}, request=request)


class Edition_trombinoscope(Edition):
    code = "trombinoscope_collaborateurs"
    titre = "Trombinoscope"
    introduction = "Imprimez les photos de l'équipe avec le nom et le poste de chaque collaborateur, regroupées par groupe ou par poste. Les photos se saisissent dans la rubrique Identité de la fiche."
    Formulaire = formulaires.Formulaire_trombinoscope

    def Imprimer(self, objets=[], parametres={}, request=None):
        from collaborateurs.utils import utils_editions_dossiers
        return utils_editions_dossiers.Impression_trombinoscope(titre=parametres["titre"], dict_donnees={"collaborateurs": objets, "parametres": parametres}, request=request)


class Edition_telephones(Edition):
    code = "liste_telephonique_collaborateurs"
    titre = "Liste téléphonique"
    introduction = "Imprimez une liste compacte des téléphones et adresses email de l'équipe, à afficher ou à emporter lors des sorties."
    Formulaire = formulaires.Formulaire_telephones
    exports = ("pdf", "xlsx")

    def Imprimer(self, objets=[], parametres={}, request=None):
        from collaborateurs.utils import utils_editions_dossiers
        return utils_editions_dossiers.Impression_telephones(titre=parametres["titre"], dict_donnees={"collaborateurs": objets, "parametres": parametres}, request=request,
                                                             taille_page=utils_editions_dossiers.Taille_page(parametres["orientation"]))

    def Exporter_xlsx(self, objets=[], parametres={}, request=None):
        from collaborateurs.utils import utils_editions_dossiers
        entetes, lignes = utils_editions_dossiers.Donnees_telephones(objets, parametres)
        return utils_editions_dossiers.Exporter_tableau_xlsx(parametres["titre"], entetes, [ligne for groupe, liste in lignes for ligne in liste])


class Edition_liste(Edition):
    code = "edition_liste_collaborateurs"
    titre = "Listing des collaborateurs"
    introduction = "Composez une liste des collaborateurs en choisissant les colonnes et le tri, puis imprimez-la en PDF ou exportez-la vers Excel."
    Formulaire = formulaires.Formulaire_liste
    exports = ("pdf", "xlsx")

    def Imprimer(self, objets=[], parametres={}, request=None):
        from collaborateurs.utils import utils_editions_dossiers
        return utils_editions_dossiers.Impression_liste(titre=parametres["titre"], dict_donnees={"collaborateurs": objets, "parametres": parametres}, request=request,
                                                        taille_page=utils_editions_dossiers.Taille_page(parametres["orientation"]))

    def Exporter_xlsx(self, objets=[], parametres={}, request=None):
        from collaborateurs.utils import utils_editions_dossiers
        entetes, lignes = utils_editions_dossiers.Donnees_liste(objets, parametres, pour_excel=True)
        return utils_editions_dossiers.Exporter_tableau_xlsx(parametres["titre"], entetes, lignes)


class Edition_etiquettes(Edition):
    code = "etiquettes_collaborateurs"
    titre = "Etiquettes et badges"
    introduction = "Imprimez des étiquettes d'adresse, des étiquettes nominatives ou des badges avec photo sur des planches standard."
    Formulaire = formulaires.Formulaire_etiquettes

    def Imprimer(self, objets=[], parametres={}, request=None):
        from collaborateurs.utils import utils_editions_dossiers
        return utils_editions_dossiers.Impression_etiquettes(objets, parametres)


# ------------------------------------------------- Réglementaire -------------------------------------------------

class Edition_registre(Edition):
    code = "registre_personnel_collaborateurs"
    titre = "Registre unique du personnel"
    introduction = "Imprimez le registre unique du personnel : une ligne par contrat, dans l'ordre des embauches, avec l'identité, l'emploi, le type de contrat et les dates d'entrée et de sortie. " \
                   "La nationalité se saisit dans la rubrique Identité de la fiche."
    Formulaire = formulaires.Formulaire_registre
    exports = ("pdf", "xlsx")

    def Imprimer(self, objets=[], parametres={}, request=None):
        from collaborateurs.utils import utils_editions_rh
        return utils_editions_rh.Impression_registre(titre=self.titre, dict_donnees={"collaborateurs": objets, "parametres": parametres}, request=request,
                                                     taille_page=utils_editions_rh.PAYSAGE)

    def Exporter_xlsx(self, objets=[], parametres={}, request=None):
        from collaborateurs.utils import utils_editions_rh, utils_editions_dossiers
        entetes, lignes = utils_editions_rh.Donnees_registre(objets, parametres)
        return utils_editions_dossiers.Exporter_tableau_xlsx(self.titre, entetes, lignes)


class Edition_qualifications(Edition):
    code = "etat_qualifications_collaborateurs"
    titre = "Etat des qualifications"
    introduction = "Imprimez le tableau des qualifications de l'équipe (BAFA, BAFD, PSC1...) avec la validité des pièces justificatives et le nombre de collaborateurs qualifiés. " \
                   "Utile pour les déclarations d'accueils collectifs de mineurs et les contrôles."
    Formulaire = formulaires.Formulaire_qualifications
    exports = ("pdf", "xlsx")

    def Imprimer(self, objets=[], parametres={}, request=None):
        from collaborateurs.utils import utils_editions_rh
        return utils_editions_rh.Impression_qualifications(titre=self.titre, dict_donnees={"collaborateurs": objets, "parametres": parametres}, request=request,
                                                           taille_page=utils_editions_rh.PAYSAGE)

    def Exporter_xlsx(self, objets=[], parametres={}, request=None):
        from collaborateurs.utils import utils_editions_rh, utils_editions_dossiers
        entetes, lignes = utils_editions_rh.Donnees_qualifications_xlsx(objets, parametres)
        return utils_editions_dossiers.Exporter_tableau_xlsx(self.titre, entetes, lignes)


# ------------------------------------------------- Congés et temps de travail -------------------------------------------------

class Edition_attestations_conges(Edition):
    code = "attestations_conges_collaborateurs"
    titre = "Attestations de congés"
    introduction = "Imprimez pour chaque collaborateur un relevé de ses compteurs de congés : droits, absences posées, demandes en attente et solde, avec le détail des absences de la période."
    Formulaire = formulaires.Formulaire_attestations_conges

    def Imprimer(self, objets=[], parametres={}, request=None):
        from collaborateurs.utils import utils_editions_temps
        return utils_editions_temps.Impression_attestations_conges(titre=self.titre, dict_donnees={"collaborateurs": objets, "parametres": parametres}, request=request)


class Edition_demandes_absences(Edition):
    code = "impression_demandes_absences_collaborateurs"
    titre = "Bons de demande d'absence"
    introduction = "Imprimez les demandes de congé et d'absence sous forme de bons à signer, avec la décision, le commentaire et le solde du compteur."
    Formulaire = formulaires.Formulaire_demandes_absences
    entetes = ["Collaborateur", "Type", "Période", "Durée", "Etat"]
    libelle_lignes = "demande"

    def Get_objets(self, user=None, parametres={}, ids=None):
        collaborateurs = utils_editions.Get_collaborateurs(user, parametres.get("situation", "tous"), parametres.get("groupes"))
        demandes = DemandeAbsenceCollaborateur.objects.select_related("collaborateur", "type_conge", "auteur", "decideur").filter(
            collaborateur_id__in=[collaborateur.pk for collaborateur in collaborateurs])
        if parametres.get("periode"):
            debut, fin = [utils_dates.ConvertDateENGtoDate(valeur) for valeur in parametres["periode"].split(";")]
            demandes = demandes.filter(date_debut__lte=fin, date_fin__gte=debut)
        if parametres.get("etats"):
            demandes = demandes.filter(etat__in=parametres["etats"])
        if ids is not None:
            demandes = demandes.filter(pk__in=ids)
        return list(demandes.order_by("date_debut", "collaborateur__nom", "collaborateur__prenom"))

    def Get_lignes(self, user=None, parametres={}):
        lignes = []
        for demande in self.Get_objets(user, parametres):
            lignes.append({"id": demande.pk, "idcollaborateur": demande.collaborateur_id, "colonnes": [demande.collaborateur.Get_nom(), demande.type_conge.nom, utils_conges.Texte_periode_demande(demande),
                                                          utils_conges.Format_valeur(demande.quantite, demande.type_conge.unite), demande.get_etat_display()]})
        return lignes

    def Imprimer(self, objets=[], parametres={}, request=None):
        from collaborateurs.utils import utils_editions_temps
        return utils_editions_temps.Impression_demandes(titre=self.titre, dict_donnees={"demandes": objets, "parametres": parametres}, request=request)


class Edition_releves_heures(Edition):
    code = "releves_heures_collaborateurs"
    titre = "Relevés mensuels d'heures"
    introduction = "Imprimez pour chaque collaborateur le relevé jour par jour de ses heures du mois (planifié, réalisé, absences), avec les totaux par semaine et une zone de signature. " \
                   "Le relevé signé sert de justificatif pour la paie."
    Formulaire = formulaires.Formulaire_releves_heures

    def Imprimer(self, objets=[], parametres={}, request=None):
        from collaborateurs.utils import utils_editions_temps
        return utils_editions_temps.Impression_releves(titre=self.titre, dict_donnees={"collaborateurs": objets, "parametres": parametres}, request=request)


EDITIONS = {edition.code: edition for edition in (Edition_fiches(), Edition_trombinoscope(), Edition_telephones(), Edition_liste(), Edition_etiquettes(),
                                                   Edition_registre(), Edition_qualifications(), Edition_attestations_conges(), Edition_demandes_absences(),
                                                   Edition_releves_heures())}


# ------------------------------------------------- Vues -------------------------------------------------

def Generer(request, code=""):
    """ Génération du PDF ou du fichier Excel pour les lignes cochées """
    edition = EDITIONS.get(code)
    if not edition:
        raise Http404
    if not request.user.has_perm("core.%s" % code):
        return JsonResponse({"erreur": "Vous n'avez pas l'autorisation d'accéder à cette fonctionnalité"}, status=403)
    form = edition.Formulaire(request.POST, request=request)
    if not form.is_valid():
        erreurs = ["%s : %s" % (form.fields[nom].label if nom in form.fields else nom, " ".join(liste)) for nom, liste in form.errors.items()]
        return JsonResponse({"erreur": "Paramètres incorrects. %s" % " ".join(erreurs)}, status=400)
    try:
        ids = [int(valeur) for valeur in json.loads(request.POST.get("coches", "[]"))]
    except (TypeError, ValueError):
        ids = []
    if not ids:
        return JsonResponse({"erreur": "Cochez au moins une ligne dans la liste"}, status=400)

    # Les lignes cochées sont recherchées parmi celles accessibles à l'utilisateur, dans l'ordre de la liste
    objets = edition.Get_objets(request.user, form.cleaned_data, ids=ids)
    if not objets:
        return JsonResponse({"erreur": "Aucune ligne cochée n'est accessible"}, status=400)
    try:
        if request.POST.get("format") == "xlsx" and "xlsx" in edition.exports:
            return JsonResponse({"url": edition.Exporter_xlsx(objets, form.cleaned_data, request)})
        resultat = edition.Imprimer(objets, form.cleaned_data, request)
    except Exception as erreur:
        logger.exception("Erreur lors de l'édition %s" % code)
        return JsonResponse({"erreur": "Erreur lors de la création du document : %s" % erreur}, status=400)
    if isinstance(resultat, JsonResponse):
        return resultat
    if getattr(resultat, "erreurs", None):
        return JsonResponse({"erreur": " ".join(resultat.erreurs)}, status=400)
    return JsonResponse({"nom_fichier": resultat.Get_nom_fichier()})


class View(CustomView, TemplateView):
    template_name = "collaborateurs/editions.html"
    code = ""

    def dispatch(self, request, *args, **kwargs):
        self.edition = EDITIONS[self.code]
        self.menu_code = self.code
        return super(View, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = self.edition.titre
        context["edition"] = self.edition
        context["box_introduction"] = self.edition.introduction
        if "form_parametres" not in kwargs:
            form = self.edition.Formulaire(request=self.request)
            parametres = form.Get_parametres()
            # Une fiche collaborateur peut ouvrir l'édition pour ce seul collaborateur
            self.idcollaborateur = self.request.GET.get("idcollaborateur")
            if self.idcollaborateur:
                parametres["situation"] = "tous"
                form.fields["situation"].initial = "tous"
            context["form_parametres"] = form
            context["lignes"] = self.edition.Get_lignes(self.request.user, parametres)
        context["preselection"] = [int(self.idcollaborateur)] if getattr(self, "idcollaborateur", None) and str(self.idcollaborateur).isdigit() else []
        return context

    def post(self, request, **kwargs):
        form = self.edition.Formulaire(request.POST, request=self.request)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form_parametres=form, lignes=[]))
        return self.render_to_response(self.get_context_data(form_parametres=form, lignes=self.edition.Get_lignes(request.user, form.cleaned_data)))
