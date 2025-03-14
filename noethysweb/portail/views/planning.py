# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json, datetime
from core.models import Rattachement
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.utils.translation import gettext as _
from django.http import HttpResponseRedirect
from django.contrib import messages
from core.models import Individu, Inscription, PortailPeriode, Vacance, Ferie, Activite, JOURS_COMPLETS_SEMAINE, AdresseMail, ModeleEmail, Mail, Destinataire
from core.utils import utils_portail
from outils.utils import utils_email
from consommations.views.grille import Get_periode, Get_generic_data, Save_grille
from consommations.forms.appliquer_semaine_type import Formulaire as form_appliquer_semaine_type
from consommations.forms.grille_forfaits import Formulaire as form_forfaits
from portail.templatetags.planning import is_modif_allowed
from portail.utils import utils_approbations
from portail.views.base import CustomView
from reglements.utils import utils_ventilation


class View(CustomView, TemplateView):
    menu_code = "portail_reservations"
    template_name = "portail/planning.html"

    def get_object(self):
        """Récupérer l'objet famille ou individu selon l'utilisateur"""
        if hasattr(self.request.user, 'famille'):
            return self.request.user.famille
        elif hasattr(self.request.user, 'individu'):
            return self.request.user.individu
        else:
            raise Http404("Utilisateur non reconnu.")

    def get_famille_object(self):
        if hasattr(self.request.user, 'famille'):
            return self.request.user.famille
        elif hasattr(self.request.user, 'individu'):
            rattachement = Rattachement.objects.filter(individu=self.request.user.individu).first()
            if rattachement.famille and rattachement.titulaire == 1:
                return rattachement.famille

        return None

    def dispatch(self, request, *args, **kwargs):
        """ Vérifie si des approbations sont requises et utilise la famille ou l'individu selon l'utilisateur """
        if not request.user.is_authenticated:
            return redirect("portail_connexion")
        # Récupération de l'objet famille ou individu
        utilisateur_obj = self.get_object()

        # Récupération de l'activité
        activite = Activite.objects.prefetch_related("types_consentements").get(pk=kwargs["idactivite"])

        # Approbations requises
        famille = self.get_famille_object()  # Toujours utiliser la famille, que l'utilisateur soit une famille ou un individu

        approbations_requises = utils_approbations.Get_approbations_requises(famille=famille,activites=[activite,],idindividu=kwargs["idindividu"])
        if approbations_requises["nbre_total"] > 0:
            messages.add_message(request, messages.ERROR, "L'accès à ces réservations nécessite au moins une approbation. Veuillez valider les approbations en attente.")
            return redirect("portail_renseignements")
        return super(View, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        famille = self.get_famille_object()  # Toujours utiliser la famille, que l'utilisateur soit une famille ou un individu

        """ Sauvegarde de la grille """
        resultat = Save_grille(request=request, donnees=json.loads(self.request.POST.get("donnees")))

        # Ventilation auto si besoin
        if utils_portail.Get_parametre(code="reservations_ventilation_auto") and utils_ventilation.GetAnomaliesVentilation(idfamille=famille.pk):
            utils_ventilation.Ventilation_auto(IDfamille=famille.pk)

        # Envoi d'un mail de confirmation des modifications
        idadresse_exp = utils_portail.Get_parametre(code="reservations_adresse_exp")
        if idadresse_exp:
            self.Envoi_mail_confirmation(request=request, resultat=resultat, idadresse_exp=idadresse_exp)

        return HttpResponseRedirect(reverse_lazy("portail_reservations"))

    def test_func(self):
        """ Vérifie que l'utilisateur peut accéder à cette page """
        if not super(View, self).test_func():
            return False

        famille = self.get_famille_object()  # Récupérer la famille peu importe le type d'utilisateur

        if not famille:
            return False

        inscription = Inscription.objects.filter(famille=famille,individu_id=self.kwargs.get('idindividu'),activite_id=self.kwargs["idactivite"])
        if not inscription.exists() or not inscription.first().internet_reservations:
            return False

        periode = PortailPeriode.objects.select_related("activite").prefetch_related("categories").get(pk=self.kwargs.get('idperiode'))
        if not periode or not periode.Is_active_today():
            return False
        if hasattr(self.request.user, 'famille') and not periode.Is_famille_authorized(famille=self.request.user.famille):
            return False

        if hasattr(self.request.user, 'individu') and not periode.Is_individu_authorized(individu=self.request.user.individu):
            return False
        return True

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = _("Planning")
        context['form_appliquer_semaine_type'] = form_appliquer_semaine_type
        context['jours_complets_semaine'] = JOURS_COMPLETS_SEMAINE
        context['data'] = self.Get_data_planning()
        if context['data']["tarifs_credits_exists"]:
            context['form_forfaits'] = form_forfaits(inscriptions=context['data']["liste_inscriptions"], is_portail=True)
        return context

    def Get_data_planning(self):
        # Initialisation des données avec la famille de l'utilisateur
        famille = self.get_famille_object()  # Utilisation de la méthode pour récupérer la famille
        data = {"mode": "portail", "idfamille": famille.pk, "consommations": {}, "prestations": {}, "memos": {},"options": {"afficher_quantites": False}}
        data["dict_suppressions"] = {"consommations": [], "prestations": [], "memos": []}

        # Importation de l'individu
        individu = Individu.objects.get(pk=self.kwargs.get('idindividu'))
        data['individu'] = individu

        # Importation de la période
        periode_reservation = PortailPeriode.objects.select_related("activite").get(pk=self.kwargs.get('idperiode'))
        data['periode_reservation'] = periode_reservation

        # Gestion des dates de la période
        afficher_dates_passees = int(periode_reservation.activite.portail_afficher_dates_passees)
        if afficher_dates_passees == 9999:
            data["date_min"] = periode_reservation.date_debut
        else:
            data["date_min"] = max([periode_reservation.date_debut, datetime.date.today() - datetime.timedelta(days=afficher_dates_passees)])
        data["date_max"] = periode_reservation.date_fin
        data["selection_activite"] = periode_reservation.activite
        data["liste_vacances"] = Vacance.objects.filter(date_fin__gte=data["date_min"], date_debut__lte=data["date_max"]).order_by("date_debut")
        data["liste_feries"] = Ferie.objects.all()

        # Création des périodes à afficher
        data["periode"] = {'mode': 'dates', 'selections': {},'periodes': ['%s;%s' % (data["date_min"], data["date_max"])]}

        if periode_reservation.type_date == "VACANCES":
            data["periode"]["periodes"] = []
            for vacance in data["liste_vacances"]:
                vac_date_debut = vacance.date_debut if vacance.date_debut > data["date_min"] else data["date_min"]
                vac_date_fin = vacance.date_fin if vacance.date_fin < data["date_max"] else data["date_max"]
                data["periode"]["periodes"].append("%s;%s" % (vac_date_debut, vac_date_fin))

        if periode_reservation.type_date == "SCOLAIRES":
            data["periode"]["periodes"] = []
            dates_scolaires = [[data["date_min"], None]]
            for vacance in data["liste_vacances"]:
                dates_scolaires[-1][1] = vacance.date_debut - datetime.timedelta(days=1)
                if dates_scolaires[-1][1] < dates_scolaires[-1][0]:
                    dates_scolaires[-1][0] = vacance.date_fin + datetime.timedelta(days=1)
                else:
                    dates_scolaires.append([vacance.date_fin + datetime.timedelta(days=1), None])
                if dates_scolaires[-1][0] > data["date_max"]:
                    dates_scolaires.pop(-1)
                else:
                    dates_scolaires[-1][1] = data["date_max"]
            if dates_scolaires and not dates_scolaires[-1][1]:
                dates_scolaires[-1][1] = data["date_max"]
            data["periode"]["periodes"] = ["%s;%s" % (periode[0], periode[1]) for periode in dates_scolaires]

        # Créatio de la condition des périodes
        data = Get_periode(data)

        # Importation de toutes les inscriptions de l'individu
        data['liste_inscriptions'] = []
        for inscription in Inscription.objects.select_related('individu', 'activite', 'groupe', 'famille', 'categorie_tarif').filter(famille=famille, individu=individu, activite=periode_reservation.activite):
            if inscription.Is_inscription_in_periode(data["date_min"], data["date_max"]):
                data['liste_inscriptions'].append(inscription)

        # Incorpore les données génériques
        data.update(Get_generic_data(data))

        # Liste des dates modifiables
        data["dates_modifiables"] = [date for date in data["liste_dates"] if is_modif_allowed(date, data)]
        if data["dates_modifiables"]:
            data["date_modifiable_min"] = min(data["dates_modifiables"]) if data["dates_modifiables"] else None
            data["date_modifiable_max"] = max(data["dates_modifiables"]) if data["dates_modifiables"] else None

        # Liste des jours de la semaine modifiables
        jours = {date.weekday(): True for date in data["dates_modifiables"]}
        data["jours_semaine_modifiables"] = list(jours.keys())

        return data

    def Envoi_mail_confirmation(self, request=None, resultat=None, idadresse_exp=None):
        """ Envoi d'un mail de confirmation des modifications """
        # Importation des données
        liste_historique = resultat["liste_historique"]
        detail_evenements = resultat["detail_evenements"]
        periode = PortailPeriode.objects.select_related("activite").prefetch_related("categories").get(pk=self.kwargs.get('idperiode'))
        individu = Individu.objects.get(pk=self.kwargs.get('idindividu'))

        # Création du texte des modifications
        dict_historique = {"ajouts": [], "suppressions": []}
        for idx, historique in enumerate(liste_historique):
            label_ajout = historique["detail"]
            if idx in detail_evenements and detail_evenements[idx]:
                label_ajout += " : %s" % detail_evenements[idx]
            if historique["titre"] == "Ajout d'une consommation": dict_historique["ajouts"].append(label_ajout)
            if historique["titre"] == "Suppression d'une consommation": dict_historique["suppressions"].append(historique["detail"])

        items_identiques = list(set(dict_historique["ajouts"]).intersection(dict_historique["suppressions"]))
        for item in items_identiques:
            dict_historique["ajouts"].remove(item)
            dict_historique["suppressions"].remove(item)

        texte_detail = ""
        for type_action in ("ajouts", "suppressions"):
            if dict_historique[type_action]:
                if type_action == "suppressions" and dict_historique["ajouts"]: texte_detail += "<br>"
                texte_detail += "<b>%s de consommations :</b><br>" % type_action.capitalize()
                texte_detail += "".join([" - %s<br>" % detail for detail in dict_historique[type_action]])

        if not texte_detail:
            return False

        # Recherche de l'adresse d'expédition du mail
        adresse_exp = None
        if idadresse_exp:
            adresse_exp = AdresseMail.objects.get(pk=idadresse_exp, actif=True)
        if not adresse_exp:
            logger.error("Aucune adresse d'expédition paramétrée pour l'envoi d'un mail de confirmation des réservations.")
            return

        # Création du mail
        logger.debug("Création du mail de confirmation des modifications...")
        modele_email = ModeleEmail.objects.filter(categorie="portail_confirmation_reservations", defaut=True).first()
        if not modele_email:
            logger.error("Erreur : Aucun modèle d'email de catégorie 'portail_confirmation_reservations' n'a été paramétré !")
            return

        mail = Mail.objects.create(
            categorie="portail_confirmation_reservations",
            objet=modele_email.objet if modele_email else "",
            html=modele_email.html if modele_email else "",
            adresse_exp=adresse_exp,
            selection="NON_ENVOYE",
            utilisateur=request.user if request else None,
        )

        # Fusion des valeurs
        valeurs_fusion = {"{DETAIL_MODIFICATIONS}": texte_detail, "{ACTIVITE_NOM}": periode.activite.nom, "{PERIODE_NOM}": periode.nom,
                          "{INDIVIDU_NOM}": individu.nom, "{INDIVIDU_PRENOM}": individu.prenom, "{INDIVIDU_NOM_COMPLET}": individu.Get_nom()}

        # Création du destinataire
        destinataire = Destinataire.objects.create(categorie="famille", famille=self.get_famille(), adresse=self.get_famille().mail, valeurs=json.dumps(valeurs_fusion))
        mail.destinataires.add(destinataire)

        # Envoi du mail
        logger.debug("Envoi du mail de confirmation des modifications de réservations.")
        utils_email.Envoyer_model_mail(idmail=mail.pk, request=request)
