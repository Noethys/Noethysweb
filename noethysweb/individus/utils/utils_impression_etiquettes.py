# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from uuid import uuid4
from django.conf import settings
from django.http import JsonResponse
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.units import mm
from core.utils import utils_modeles_documents, utils_infos_individus, utils_impression, utils_fichiers


def Impression(dict_options={}):

    def AfficheReperesDecoupe():
        if dict_options["reperes"] == True:
            canvas.setStrokeColor((0.9, 0.9, 0.9))
            canvas.setLineWidth(0.25)
            # Repères de colonnes
            for y1, y2 in [(dict_options["hauteur"] * mm - 4 * mm, dict_options["hauteur"] * mm - dict_options["marge_haut"] * mm + 2 * mm), (4 * mm, dict_options["marge_bas"] - 2 * mm)]:
                x = dict_options["marge_gauche"] * mm
                for numColonne in range(0, int(nbre_colonnes)):
                    canvas.line(x, y1, x, y2)
                    x += modele_doc.modele.largeur * mm
                    canvas.line(x, y1, x, y2)
                    x += dict_options["espace_horizontal"] * mm
            # Repères de lignes
            for x1, x2 in [(4 * mm, dict_options["marge_gauche"] * mm - 2 * mm), (dict_options["largeur"] * mm - 4 * mm, dict_options["largeur"] * mm - dict_options["marge_droite"] * mm + 2 * mm)]:
                y = dict_options["hauteur"] * mm - dict_options["marge_haut"] * mm
                for numLigne in range(0, int(nbre_lignes)):
                    canvas.line(x1, y, x2, y)
                    y -= modele_doc.modele.hauteur * mm
                    canvas.line(x1, y, x2, y)
                    y -= dict_options["espace_vertical"] * mm

    # Créé le répertoire temp s'il n'existe pas
    rep_temp = utils_fichiers.GetTempRep()

    # Initialisation du fichier
    nom_fichier = "/temp/%s.pdf" % uuid4()
    chemin_fichier = settings.MEDIA_ROOT + nom_fichier
    canvas = Canvas(chemin_fichier, pagesize=utils_modeles_documents.ConvertTailleModeleEnPx((float(dict_options["largeur"]), float(dict_options["hauteur"]))))
    canvas.setTitle("Etiquettes et badges")

    # Initialisation du modèle de document
    modele_doc = utils_modeles_documents.Modele_doc(IDmodele=dict_options["modele"].pk)
    taille_modele = utils_modeles_documents.ConvertTailleModeleEnPx((modele_doc.modele.largeur, modele_doc.modele.hauteur))

    # Calcul du nbre de colonnes et de lignes
    nbre_colonnes = (dict_options["largeur"] - dict_options["marge_gauche"] - dict_options["marge_droite"] + dict_options["espace_horizontal"]) / (modele_doc.modele.largeur + dict_options["espace_horizontal"])
    nbre_lignes = (dict_options["hauteur"] - dict_options["marge_haut"] - dict_options["marge_bas"] + dict_options["espace_vertical"]) / (modele_doc.modele.hauteur + dict_options["espace_vertical"])

    # Recherche les valeurs de fusion
    infosIndividus = utils_infos_individus.Informations(qf=True, inscriptions=True, messages=False, infosMedicales=False, cotisationsManquantes=False,
                                                        piecesManquantes=False, questionnaires=True, scolarite=True)
    dict_infos = infosIndividus.GetDictValeurs(mode=dict_options["categorie"], ID=None, formatChamp=True)

    # Ajoute les données de l'organisateur
    motscles_defaut = utils_impression.Get_motscles_defaut()

    # Création des étiquettes
    numColonne = 0
    numLigne = 0
    for ID in dict_options["coches"]:
        dict_valeurs = dict_infos[ID]
        dict_valeurs.update(motscles_defaut)

        for num_copie in range(0, dict_options["nbre_copies"]):
            x = dict_options["marge_gauche"] + ((modele_doc.modele.largeur + dict_options["espace_horizontal"]) * numColonne)
            y = dict_options["hauteur"] - dict_options["marge_haut"] - ((modele_doc.modele.hauteur + dict_options["espace_vertical"]) * numLigne)

            # Positionnement sur la feuille
            canvas.saveState()
            canvas.translate(x * mm, y * mm)
            canvas.scale(1, -1)

            # Création du clipping
            p = canvas.beginPath()
            canvas.setStrokeColor((1, 1, 1))
            canvas.setLineWidth(0.25)
            p.rect(0, 0, modele_doc.modele.largeur * mm, modele_doc.modele.hauteur * mm)
            canvas.clipPath(p)

            # Dessin de l'étiquette
            modele_doc.DessineFond(canvas, dict_valeurs=dict_valeurs, options={"translate": False})
            etat = modele_doc.DessineTousObjets(canvas, dict_valeurs=dict_valeurs, options={"translate": False})
            if etat == False:
                return

            # Dessin du contour de l'étiquette
            if dict_options["contours"]:
                canvas.setStrokeColor((0, 0, 0))
                canvas.setLineWidth(0.25)
                canvas.rect(0, 0, modele_doc.modele.largeur * mm, modele_doc.modele.hauteur * mm)

            canvas.restoreState()

            # Saut de colonne
            numColonne += 1
            # Saut de ligne
            if numColonne > nbre_colonnes - 1:
                numLigne += 1
                numColonne = 0
            # Saut de page
            if numLigne > nbre_lignes - 1:
                AfficheReperesDecoupe()
                canvas.showPage()
                numLigne = 0

    # Affichage des repères de découpe
    AfficheReperesDecoupe()

    # Finalisation du PDF
    canvas.save()
    return JsonResponse({"nom_fichier": nom_fichier})
