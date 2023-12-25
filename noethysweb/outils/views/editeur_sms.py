# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseRedirect
from django.db.models import Q, Count
from django.contrib import messages
from core.views import crud
from core.models import SMS, DestinataireSMS, Famille, Individu, Collaborateur, ModeleSMS
from core.utils import utils_texte
from outils.forms.editeur_sms import Formulaire
from outils.utils import utils_sms


def Get_modele_sms(request):
    """ Renvoie le contenu d'un modèle de SMS """
    idmodele = int(request.POST.get("idmodele"))
    modele = ModeleSMS.objects.filter(pk=idmodele).first()
    return JsonResponse({"objet": modele.objet, "texte": modele.texte})


class Page(crud.Page):
    model = SMS
    menu_code = "editeur_sms"
    template_name = "outils/editeur_sms.html"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['page_titre'] = "Editeur de SMS"
        context['afficher_menu_brothers'] = True
        context['categories'] = {} if not self.Get_idsms() else {item["categorie"]: item["nbre"] for item in DestinataireSMS.objects.values('categorie').filter(sms=self.Get_idsms()).annotate(nbre=Count("pk"))}
        sms = SMS.objects.get(pk=self.Get_idsms()) if self.Get_idsms() else None
        context['sms'] = sms

        # Importe la liste des destinataires (Elimine les doublons)
        destinataires, adresses_temp = [], []
        nbre_envois_attente, nbre_envois_reussis, nbre_envois_echec = 0, 0, 0
        if self.Get_idsms():
            for destinataire in DestinataireSMS.objects.select_related("famille", "individu", "collaborateur").filter(sms=self.Get_idsms()).order_by("mobile"):
                if True:#destinataire.adresse not in adresses_temp:
                    destinataires.append(destinataire)
                    adresses_temp.append(destinataire.mobile)
                    if not destinataire.resultat_envoi:
                        nbre_envois_attente += 1
                    elif destinataire.resultat_envoi == "ok":
                        nbre_envois_reussis += 1
                    else:
                        nbre_envois_echec += 1
        context['destinataires'] = destinataires
        context['nbre_envois_attente'] = nbre_envois_attente
        context['nbre_envois_echec'] = nbre_envois_echec
        context['nbre_envois_reussis'] = nbre_envois_reussis

        # Création du texte d'intro de la box Envois
        intro_envois = []
        if not destinataires: intro_envois.append("Aucun envoi")
        if nbre_envois_reussis: intro_envois.append("%d envois réussis" % nbre_envois_reussis) if nbre_envois_reussis > 1 else intro_envois.append("1 envoi réussi")
        if nbre_envois_attente: intro_envois.append("%d envois en attente" % nbre_envois_attente) if nbre_envois_attente > 1 else intro_envois.append("1 envoi en attente")
        if nbre_envois_echec: intro_envois.append("%d envois en échec" % nbre_envois_echec) if nbre_envois_echec > 1 else intro_envois.append("1 envoi en échec")
        context['intro_envoi'] = utils_texte.Convert_liste_to_texte_virgules(intro_envois)

        return context

    def Get_idsms(self):
        return self.kwargs.get('pk', None)

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idactivite au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idsms"] = self.Get_idsms()
        return form_kwargs

    def post(self, request, *args, **kwargs):
        # Validation du formulaire
        form = Formulaire(request.POST, request=self.request)
        if form.is_valid() == False:
            return self.render_to_response(self.get_context_data(form=form))

        idsms = self.kwargs.get("pk")

        # Modification du SMS
        if idsms:
            sms = SMS.objects.get(pk=idsms)
            sms.objet = form.cleaned_data.get("objet")
            sms.texte = form.cleaned_data.get("texte")
            sms.configuration_sms = form.cleaned_data.get("configuration_sms")
            sms.selection = form.cleaned_data.get("selection")
            sms.save()

        # Création du SMS
        if not idsms:
            sms = SMS.objects.create(
                objet=form.cleaned_data.get("objet"),
                texte=form.cleaned_data.get("texte"),
                configuration_sms=form.cleaned_data.get("configuration_sms"),
                selection=form.cleaned_data.get("selection"),
                utilisateur=request.user,
            )
            messages.add_message(request, messages.INFO, "Un brouillon du SMS a été enregistré")

        # Redirection vers pages de sélection des destinataires
        action = request.POST.get("action")
        if action == "ajouter_familles": return HttpResponseRedirect(reverse_lazy("editeur_sms_familles", kwargs={"idsms": sms.pk}))
        if action == "ajouter_individus": return HttpResponseRedirect(reverse_lazy("editeur_sms_individus", kwargs={"idsms": sms.pk}))
        if action == "ajouter_collaborateurs": return HttpResponseRedirect(reverse_lazy("editeur_sms_collaborateurs", kwargs={"idsms": sms.pk}))
        if action == "ajouter_saisie_libre": return HttpResponseRedirect(reverse_lazy("editeur_sms_saisie_libre", kwargs={"idsms": sms.pk}))

        # Envoyer
        if action == "envoyer":
            if not sms.destinataires:
                messages.add_message(request, messages.ERROR, "Vous devez sélectionner au moins un destinataire")
            elif not form.cleaned_data.get("configuration_sms"):
                messages.add_message(request, messages.ERROR, "Vous devez sélectionner une configuration SMS dans la liste")
            elif not form.cleaned_data.get("objet"):
                messages.add_message(request, messages.ERROR, "Vous devez saisir un objet")
            elif not form.cleaned_data.get("texte"):
                messages.add_message(request, messages.ERROR, "Vous devez saisir un texte")
            else:
                utils_sms.Envoyer_model_sms(idsms=sms.pk, request=request)

        return HttpResponseRedirect(reverse_lazy("editeur_sms", kwargs={'pk': sms.pk}))


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


# -------------------------------------------------------------------------------------------

class Page_destinataires(crud.Page):
    menu_code = "editeur_sms"

    def get_context_data(self, **kwargs):
        context = super(Page_destinataires, self).get_context_data(**kwargs)
        context['page_titre'] = "Editeur de SMS"
        context['idsms'] = self.kwargs.get("idsms")
        context['categorie'] = self.categorie
        return context

    def post(self, request, **kwargs):
        liste_selections = json.loads(request.POST.get("selections"))

        # Importe le SMS
        sms = SMS.objects.get(pk=self.kwargs.get("idsms"))

        # Importe les numéros
        dict_numeros = {}
        if self.categorie == "famille":
            dict_numeros = {famille.pk: famille.mobile for famille in Famille.objects.filter(mobile_blocage=False)}
        if self.categorie == "individu":
            dict_numeros = {individu.pk: individu.tel_mobile for individu in Individu.objects.all()}
        if self.categorie == "collaborateur":
            dict_numeros = {collaborateur.pk: collaborateur.tel_mobile for collaborateur in Collaborateur.objects.all()}

        # Importe la liste des destinataires actuels
        destinataires = DestinataireSMS.objects.filter(categorie=self.categorie, sms=sms)
        liste_id = [getattr(destinataire, "%s_id" % self.categorie) for destinataire in destinataires]

        # Recherche le dernier ID de la table Destinataires
        dernier_destinataire = DestinataireSMS.objects.last()
        idmax = dernier_destinataire.pk if dernier_destinataire else 0

        # Ajout des destinataires
        liste_ajouts = []
        for id in liste_selections:
            if id not in liste_id:
                mobile = dict_numeros.get(id, None)
                if mobile:
                    kwargs = {"{0}_id".format(self.categorie): id, "categorie": self.categorie, "mobile": mobile}
                    liste_ajouts.append(DestinataireSMS(**kwargs))
        if liste_ajouts:
            # Enregistre les destinataires
            DestinataireSMS.objects.bulk_create(liste_ajouts)
            # Associe les destinataires au SMS
            destinataires = DestinataireSMS.objects.filter(pk__gt=idmax)
            ThroughModel = SMS.destinataires.through
            ThroughModel.objects.bulk_create([ThroughModel(sms_id=sms.pk, destinatairesms_id=destinataire.pk) for destinataire in destinataires])

        # Suppression des destinataires
        for id in liste_id:
            if id not in liste_selections:
                kwargs = {"{0}_id".format(self.categorie): id, "sms": sms}
                destinataire = DestinataireSMS.objects.get(**kwargs)
                destinataire.delete()

        return HttpResponseRedirect(reverse_lazy("editeur_sms", kwargs={'pk': sms.pk}))
