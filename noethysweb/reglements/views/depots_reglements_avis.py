# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json, datetime
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib import messages
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Depot, Reglement, ModeleEmail, Mail, Destinataire
from core.utils import utils_preferences, utils_dates


class Liste(crud.Page, crud.Liste):
    template_name = "reglements/depots_reglements_selection.html"
    menu_code = "depots_reglements_liste"
    model = Reglement
    objet_pluriel = "des règlements"

    def get_queryset(self):
        depot = Depot.objects.get(pk=self.kwargs["iddepot"])
        return Reglement.objects.select_related('mode', 'emetteur', 'famille', 'payeur').filter(self.Get_filtres("Q"), depot=depot)

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['box_titre'] = "Sélection des avis à envoyer"
        context['box_introduction'] = "Cochez les règlements pour lesquels vous souhaitez envoyer un avis de dépôt par email. Puis cliquez sur Valider pour accéder à l'éditeur d'emails."
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        context["hauteur_table"] = "400px"
        context['iddepot'] = self.kwargs.get("iddepot")
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:famille", "idreglement", "date", "mode__label", "emetteur__nom", "numero_piece", "payeur__nom",
                   "montant", "compte", "date_differe", "observations", "famille__email_depots", "avis_depot"]
        check = columns.CheckBoxSelectColumn(label="")
        mode = columns.TextColumn("Mode", sources=['mode__label'])
        emetteur = columns.CompoundColumn("Emetteur", sources=['emetteur__nom'])
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        payeur = columns.TextColumn("Payeur", sources=['payeur__nom'])
        email_depots = columns.BooleanColumn("Avis activé", sources=["famille__email_depots"], processor="Formate_activation")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idreglement", "email_depots", "avis_depot", "date", "mode", "emetteur", "numero_piece", "montant", "famille", "payeur", "date_differe", "compte", "observations"]
            hidden_columns = ["compte", "observations", "date_differe"]
            processors = {
                "date": helpers.format_date('%d/%m/%Y'),
                "date_differe": helpers.format_date('%d/%m/%Y'),
                "avis_depot": helpers.format_date('%d/%m/%Y'),
                "montant": "Formate_montant",
            }
            labels = {
                "date_differe": "Différé",
                "avis_depot": "Date avis",
            }
            ordering = ["-idreglement"]

        def Formate_montant(self, instance, **kwargs):
            return "%0.2f %s" % (instance.montant, utils_preferences.Get_symbole_monnaie())

        def Formate_activation(self, instance, **kwargs):
            if instance.famille.email_depots:
                return "<span class='badge bg-success'><i class='fa fa-check margin-r-5'></i>Oui</span>"
            else:
                return "<span class='badge bg-danger'><i class='fa fa-close margin-r-5'></i>Non</span>"


    def post(self, request, **kwargs):
        iddepot = self.kwargs.get("iddepot")
        liste_selections = json.loads(request.POST.get("selections"))

        if not liste_selections:
            messages.add_message(request, messages.ERROR, "Vous devez cocher au moins une ligne dans la liste")
            return HttpResponseRedirect(reverse_lazy("depots_reglements_envoyer_avis", kwargs={"iddepot": iddepot}))

        # Création du mail
        logger.debug("Création d'un nouveau mail...")
        modele_email = ModeleEmail.objects.filter(categorie="reglement", defaut=True).first()
        mail = Mail.objects.create(categorie="reglement",
            objet=modele_email.objet if modele_email else "", html=modele_email.html if modele_email else "",
            adresse_exp=request.user.Get_adresse_exp_defaut(), selection="NON_ENVOYE", verrouillage_destinataires=True,
            utilisateur=request.user)

        # Importation des règlements
        reglements = Reglement.objects.select_related("mode", "emetteur", "famille", "payeur").filter(pk__in=liste_selections)

        # Création des destinataires
        logger.debug("Enregistrement des destinataires...")
        liste_anomalies = []
        for reglement in reglements:
            valeurs_fusion = {
                "{ID_REGLEMENT}": str(reglement.pk),
                "{DATE_REGLEMENT}": utils_dates.ConvertDateToFR(reglement.date) if reglement.date else "",
                "{MODE_REGLEMENT}": reglement.mode.label,
                "{NOM_EMETTEUR}": reglement.emetteur.nom if reglement.emetteur else "",
                "{NUM_PIECE}": reglement.numero_piece,
                "{MONTANT_REGLEMENT}": "%0.2f %s" % (reglement.montant, utils_preferences.Get_symbole_monnaie()),
                "{NOM_PAYEUR}": reglement.payeur.nom,
                "{NUM_QUITTANCIER}": reglement.numero_quittancier,
                "{DATE_SAISIE}": utils_dates.ConvertDateToFR(reglement.date_saisie),
                "{DATE_DIFFERE}": utils_dates.ConvertDateToFR(reglement.date_differe) if reglement.date_differe else "",
            }
            if reglement.famille.mail:
                # Création du destinataire
                destinataire = Destinataire.objects.create(categorie="famille", famille=reglement.famille, adresse=reglement.famille.mail, valeurs=json.dumps(valeurs_fusion))
                mail.destinataires.add(destinataire)
                # Enregistrement de la date d'envoi de l'avis
                reglement.avis_depot = datetime.date.today()
                reglement.save()
            else:
                liste_anomalies.append(reglement.famille.nom)

        if liste_anomalies:
            messages.add_message(request, messages.ERROR, "Adresses mail manquantes : %s" % ", ".join(liste_anomalies))

        # Redirection vers l'éditeur d'emails
        logger.debug("Redirection vers l'éditeur d'emails...")
        return HttpResponseRedirect(reverse_lazy("editeur_emails", kwargs={'pk': mail.pk}))
