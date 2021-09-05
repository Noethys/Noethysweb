# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views import crud
from core.models import ListeDiffusion, Destinataire, Mail, Individu
from core.views.mydatatableview import MyDatatable, columns, helpers
from outils.views.editeur_emails import Page_destinataires
from django.http import HttpResponseRedirect
from django.db.models import Q, Count
import json


class Liste(Page_destinataires, crud.Liste):
    model = ListeDiffusion
    template_name = "outils/editeur_emails_destinataires.html"
    categorie = "liste_diffusion"

    def get_queryset(self):
        return ListeDiffusion.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['box_titre'] = "Sélection de listes de diffusion"
        context['box_introduction'] = "Sélectionnez des listes de diffusion ci-dessous."
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        context["hauteur_table"] = "400px"
        context['liste_coches'] = [destinataire.liste_diffusion_id for destinataire in Destinataire.objects.filter(categorie="liste_diffusion", mail=self.kwargs.get("idmail"))]
        return context

    class datatable_class(MyDatatable):
        filtres = ["idliste", "nom"]
        check = columns.CheckBoxSelectColumn(label="")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', "idliste", "nom"]
            ordering = ["nom"]

    def post(self, request, **kwargs):
        liste_selections = json.loads(request.POST.get("selections"))

        # Importe le mail
        mail = Mail.objects.get(pk=self.kwargs.get("idmail"))

        # Récupère la liste des listes de diffusion cochées
        liste_id = [item["liste_diffusion"] for item in Destinataire.objects.values('liste_diffusion').filter(categorie="liste_diffusion", mail=mail).annotate(total=Count("pk"))]

        # Recherche le dernier ID de la table Destinataires
        dernier_destinataire = Destinataire.objects.last()
        idmax = dernier_destinataire.pk if dernier_destinataire else 0

        # Ajout des destinataires
        liste_ajouts = []
        for id in liste_selections:
            if id not in liste_id:
                for individu in Individu.objects.filter(listes_diffusion=id):
                    if individu.mail:
                        kwargs = {"{0}_id".format(self.categorie): id, "categorie": self.categorie, "individu": individu, "adresse": individu.mail}
                        liste_ajouts.append(Destinataire(**kwargs))
        if liste_ajouts:
            # Enregistre les destinataires
            Destinataire.objects.bulk_create(liste_ajouts)
            # Associe les destinataires au mail
            destinataires = Destinataire.objects.filter(pk__gt=idmax)
            ThroughModel = Mail.destinataires.through
            ThroughModel.objects.bulk_create([ThroughModel(mail_id=mail.pk, destinataire_id=destinataire.pk) for destinataire in destinataires])

        # Suppression des destinataires
        for id in liste_id:
            if id not in liste_selections:
                destinataires = Destinataire.objects.filter(liste_diffusion_id=id, mail=mail)
                destinataires.delete()

        return HttpResponseRedirect(reverse_lazy("editeur_emails", kwargs={'pk': mail.pk}))
