# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json, datetime, time
logger = logging.getLogger(__name__)
from decimal import Decimal
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Max, Sum
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Famille, Prestation, Reglement, Rattachement, Note, Piece, QuestionnaireReponse, Information, Vaccin
from core.models import Mandat, Payeur, Historique, Lien, Destinataire, ContactUrgence, Assurance, PortailMessage, Scolarite, Inscription
from core.utils import utils_texte


def Effacer_attributs(objet=None, attributs=[]):
    for attribut in attributs:
        try:
            setattr(objet, attribut, None)
        except Exception as e:
            # Loggez l'erreur ici si nécessaire
            print(f"Erreur lors de l'effacement de l'attribut {attribut} : {e}")
    try:
        objet.save()  # Assurez-vous que l'objet est sauvegardé après l'effacement
    except Exception as e:
        print(f"Erreur lors de l'enregistrement de l'objet {objet}: {e}")


def Effacer(request):
    time.sleep(1)

    # Récupération des comptes cochés
    coches = json.loads(request.POST.get("coches"))
    if not coches:
        return JsonResponse({"erreur": "Veuillez cocher au moins une famille dans la liste"}, status=401)

    # Vérifications des anomalies (prestations ou factures récentes)
    liste_anomalies = []
    today = datetime.date.today()
    for famille in Famille.objects.filter(pk__in=coches).annotate(
            derniere_prestation=Max("prestation__date"),
            derniere_facture=Max("facture__date_edition")
    ):
        if famille.derniere_prestation and (today - famille.derniere_prestation).days < 60:
            liste_anomalies.append(famille)
        if famille.derniere_facture and (today - famille.derniere_facture).days < 60:
            liste_anomalies.append(famille)

    if liste_anomalies:
        familles_str = ", ".join([famille.nom for famille in liste_anomalies])
        return JsonResponse({"erreur": f"Procédure annulée : Les familles suivantes ont une activité trop récente : {familles_str}."}, status=401)

    # Effacer les fiches familles
    for famille in Famille.objects.filter(pk__in=coches):

        # Mise à jour des champs de la famille
        famille.nom = "Famille effacée"
        famille.internet_actif = False
        Effacer_attributs(famille, [
            "caisse", "num_allocataire", "allocataire", "memo", "email_factures_adresses",
            "email_recus_adresses", "email_depots_adresses", "rue_resid", "cp_resid", "ville_resid",
            "secteur", "mail", "mobile", "code_compta"
        ])
        famille.save()

        # Suppression des objets liés
        Note.objects.filter(famille=famille).delete()
        Piece.objects.filter(famille=famille).delete()
        QuestionnaireReponse.objects.filter(famille=famille).delete()
        PortailMessage.objects.filter(famille=famille).delete()

        # Mandats
        for mandat in Mandat.objects.filter(famille=famille):
            Effacer_attributs(mandat, ["individu", "individu_nom", "individu_rue", "individu_cp", "individu_ville"])
            mandat.iban = "XXX"
            mandat.bic = "XXX"
            mandat.save()

        # Autres tables liées à la famille
        Payeur.objects.filter(famille=famille).update(nom="Payeur effacé")
        Historique.objects.filter(famille=famille).delete()
        Lien.objects.filter(famille=famille).delete()
        Destinataire.objects.filter(famille=famille).delete()
        ContactUrgence.objects.filter(famille=famille).delete()
        Assurance.objects.filter(famille=famille).delete()

        # Individus rattachés
        for rattachement in Rattachement.objects.select_related("individu").filter(famille=famille):
            rattachement.individu.nom = "Individu effacé"
            Effacer_attributs(rattachement.individu, [
                "nom_jfille", "prenom", "date_naiss", "cp_naiss", "ville_naiss",
                "annee_deces", "adresse_auto", "rue_resid", "cp_resid", "ville_resid", "secteur",
                "categorie_travail", "profession", "employeur", "travail_tel", "travail_fax", "travail_mail",
                "tel_domicile", "tel_mobile", "tel_fax", "mail", "medecin", "memo", "type_sieste",
                "situation_familiale", "info_garde",
            ])
            rattachement.individu.listes_diffusion.clear()
            rattachement.individu.regimes_alimentaires.clear()
            rattachement.individu.maladies.clear()
            rattachement.individu.save()
            rattachement.individu.photo.delete(save=True)

            # Inscriptions
            Inscription.objects.filter(individu=rattachement.individu, date_fin__isnull=True).update(date_fin=datetime.date.today())

            # Autres tables liées à l'individu
            Information.objects.filter(individu=rattachement.individu).delete()
            Vaccin.objects.filter(individu=rattachement.individu).delete()
            Note.objects.filter(individu=rattachement.individu).delete()
            Piece.objects.filter(individu=rattachement.individu).delete()
            QuestionnaireReponse.objects.filter(individu=rattachement.individu).delete()
            Scolarite.objects.filter(individu=rattachement.individu).delete()

    # Réactualisation de la page
    messages.add_message(request, messages.SUCCESS, "%d fiches familles ont été effacées avec succès" % len(coches))
    return JsonResponse({"url": reverse_lazy("effacer_familles")})

class Page(crud.Page):
    model = Famille
    url_liste = "effacer_familles"
    menu_code = "effacer_familles"


class Liste(Page, crud.Liste):
    template_name = "individus/effacer_familles.html"
    model = Famille

    def get_queryset(self):
        return Famille.objects.filter(self.Get_filtres("Q")).annotate(derniere_action=Max("historique__horodatage"), derniere_prestation=Max("prestation__date"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Effacer des familles"
        context['box_titre'] = "Liste des familles"
        context['box_introduction'] = "Vous pouvez ici effacer des fiches familles. Conformément au RGPD, cette fonctionnalité irréversible ne supprime pas les fiches mais les anonymise afin d'effacer les traces de familles qui ne fréquentent plus la structure. Les données importantes telles que les consommations, prestations ou règlements par exemple sont conservées afin de ne pas corrompre les statistiques."
        context['onglet_actif'] = "effacer_familles"
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        context["hauteur_table"] = "400px"
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:pk", "idfamille", "derniere_action"]
        check = columns.CheckBoxSelectColumn(label="")
        solde = columns.TextColumn("Solde", sources=None, processor="Get_solde")
        rattachements = columns.TextColumn("Individus rattachés", sources=None, processor="Get_rattachements")
        derniere_prestation = columns.TextColumn("Dernière prestation", sources=None, processor=helpers.format_date('%d/%m/%Y'))
        derniere_action = columns.TextColumn("Dernière action", sources=None, processor=helpers.format_date('%d/%m/%Y'))
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idfamille", "nom", "rattachements", "solde", "derniere_action", "derniere_prestation", "actions"]
            ordering = ["nom"]

        def Get_rattachements(self, instance, *args, **kwargs):
            if not hasattr(self, "dict_rattachements"):
                self.dict_rattachements = {}
                for rattachement in Rattachement.objects.select_related("individu").all().order_by("categorie"):
                    self.dict_rattachements.setdefault(rattachement.famille_id, [])
                    self.dict_rattachements[rattachement.famille_id].append(rattachement.individu)
            return ", ".join([individu.Get_nom() for individu in self.dict_rattachements.get(instance.pk, [])])

        def Get_solde(self, instance, *args, **kwargs):
            if not hasattr(self, "dict_prestations"):
                self.dict_prestations = {temp["famille_id"]: temp["total"] for temp in Prestation.objects.values("famille_id").annotate(total=Sum("montant"))}
                self.dict_reglements = {temp["famille_id"]: temp["total"] for temp in Reglement.objects.values("famille_id").annotate(total=Sum("montant"))}
            solde = self.dict_reglements.get(instance.pk, Decimal(0)) - self.dict_prestations.get(instance.pk, Decimal(0))
            if solde == Decimal(0):
                couleur = "success"
            elif solde > Decimal(0):
                couleur = "info"
            else:
                couleur = "danger"
            return """<span class='badge badge-%s'>%s</span>""" % (couleur, utils_texte.Formate_montant(solde))

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton(url=reverse("famille_resume", args=[instance.pk]), title="Ouvrir la fiche famille", icone="fa-users", args="target='_blank'"),
            ]
            return self.Create_boutons_actions(html)
