# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.utils.translation import gettext as _
from portail.views.fiche import Onglet, ConsulterBase
from portail.forms.individu_medecin import Formulaire
from portail.forms.medecins import Formulaire as Formulaire_medecin


def Ajouter_medecin(request):
    """ Ajouter un médecin dans la liste de choix """
    valeurs = json.loads(request.POST.get("valeurs"))

    # Formatage des champs
    valeurs["nom"] = valeurs["nom"].upper()
    valeurs["prenom"] = valeurs["prenom"].title()
    valeurs["rue_resid"] = valeurs["rue_resid"].title()
    valeurs["ville_resid"] = valeurs["ville_resid"].upper()

    # Vérification des données saisies
    form = Formulaire_medecin(valeurs)
    if not form.is_valid():
        messages_erreurs = ["%s : %s" % (field.title(), erreur[0].message) for field, erreur in form.errors.as_data().items()]
        return JsonResponse({"erreur": ", ".join(messages_erreurs)}, status=401)

    # Sauvegarde du médecin
    instance = form.save()
    return JsonResponse({"id": instance.pk, "nom": instance.Get_nom(afficher_ville=True)})


class Consulter(Onglet, ConsulterBase):
    form_class = Formulaire
    template_name = "portail/individu_medecin.html"
    mode = "CONSULTATION"
    onglet_actif = "individu_medecin"
    categorie = "individu_medecin"
    titre_historique = _("Modifier le médecin")

    def get_context_data(self, **kwargs):
        context = super(Consulter, self).get_context_data(**kwargs)
        context['box_titre'] = _("Médecin traitant")
        context['box_introduction'] = _("Cliquez sur le bouton Modifier au bas de la page pour modifier une des informations ci-dessous.")
        context['onglet_actif'] = self.onglet_actif
        return context

    def get_object(self):
        return self.get_individu()


class Modifier(Consulter):
    mode = "EDITION"

    def get_context_data(self, **kwargs):
        context = super(Modifier, self).get_context_data(**kwargs)
        context['box_introduction'] = _("Sélectionnez un médecin dans le champ ci-dessous et cliquez sur le bouton Enregistrer.")
        if not self.get_dict_onglet_actif().validation_auto:
            context['box_introduction'] += " " + _("Ces informations devront être validées par l'administrateur de l'application.")
        context['form_ajout'] = Formulaire_medecin()
        return context

    def get_success_url(self):
        return reverse_lazy("portail_individu_medecin", kwargs={'idrattachement': self.kwargs['idrattachement']})
