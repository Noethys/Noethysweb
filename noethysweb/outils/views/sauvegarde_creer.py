# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from core.views.base import CustomView
from django.views.generic import TemplateView
from outils.forms.sauvegarde_creer import Formulaire
from django.conf import settings
from core.utils import utils_cryptage_fichier
from django.contrib import messages
from django.core.management import call_command
import os, shutil
from django.http import HttpResponse



class View(CustomView, TemplateView):
    menu_code = "sauvegarde_creer"
    template_name = "core/crud/edit.html"
    compatible_demo = False

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Sauvegarde"
        context['box_titre'] = "Créer une sauvegarde"
        context['box_introduction'] = "Saisissez le mot de passe de votre choix et cliquez sur le bouton Sauvegarder. Cette fonctionnalité n'est accessible qu'aux superutilisateurs."
        context['afficher_menu_brothers'] = True
        context['form'] = context.get("form", Formulaire)
        return context

    def post(self, request, **kwargs):
        # Validation du form
        form = Formulaire(request.POST, request.FILES)
        if form.is_valid() == False:
            return self.render_to_response(self.get_context_data(form=form))

        # Vérification du mot de passe
        if form.cleaned_data.get("mdp1") != form.cleaned_data.get("mdp2"):
            messages.add_message(request, messages.ERROR, "La confirmation du mot de passe semble différente du mot de passe")
            return self.render_to_response(self.get_context_data(form=form))

        # Vérifie que l'utilisateur est un superutilisateur
        if not self.request.user.is_superuser:
            messages.add_message(request, messages.ERROR, "Vous n'êtes pas autorisé à effectuer cette opération. La sauvegarde est réservée au superutilisateurs")
            return self.render_to_response(self.get_context_data(form=form))

        # Création du répertoire de travail
        rep_destination = settings.MEDIA_ROOT + "/temp/sauvegarde"
        if not os.path.isdir(rep_destination):
            os.mkdir(rep_destination)

        def Nettoyer():
            shutil.rmtree(rep_destination)

        # Sauvegarde du core.json
        nom_fichier_core = os.path.join(rep_destination, "core.json")
        output = open(nom_fichier_core, 'w')
        call_command('dumpdata', format='json', indent=2, stdout=output, verbosity=3)
        output.close()

        # Récupération des media
        if form.cleaned_data.get("inclure_media", False):
            from distutils.dir_util import copy_tree
            rep_tmp_media = os.path.join(rep_destination, "media")
            if not os.path.isdir(rep_tmp_media):
                os.mkdir(rep_tmp_media)
            for rep in os.listdir(settings.MEDIA_ROOT):
                if rep != "temp":
                    copy_tree(os.path.join(settings.MEDIA_ROOT, rep), os.path.join(rep_tmp_media, rep))

        # Compression
        fichier_zip = shutil.make_archive(os.path.join(settings.MEDIA_ROOT, "temp", form.cleaned_data.get("nom")), 'zip', rep_destination)

        # Cryptage
        nom_fichier_nweb = os.path.join(settings.MEDIA_ROOT, "temp", form.cleaned_data.get("nom") + ".nweb")
        utils_cryptage_fichier.CrypterFichier(fichier_zip, nom_fichier_nweb, form.cleaned_data.get("mdp1"), ancienne_methode=False)

        # Nettoyage du répertoire de travail
        os.remove(fichier_zip)
        Nettoyer()

        messages.success(request, "La sauvegarde est terminée")
        with open(nom_fichier_nweb, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="application/noethysweb")
            response['Content-Disposition'] = 'inline; filename=' + os.path.basename(nom_fichier_nweb)
            return response
