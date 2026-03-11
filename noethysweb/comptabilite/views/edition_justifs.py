# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, time
from django.http import JsonResponse
from django.views.generic import TemplateView
from core.views.base import CustomView
from core.utils import utils_dates
from comptabilite.forms.edition_justifs import Formulaire
import io
from datetime import datetime
from django.template.loader import render_to_string
from django.conf import settings
from django.core.files.storage import default_storage
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from core.models import ComptaOperation
from django.utils.html import strip_tags
from django.core.files.base import ContentFile
from PIL import Image  # Pour traiter l'image (si nécessaire)

# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import io, time
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter
from PIL import Image, ImageOps  # ImageOps est crucial pour la rotation auto
from core.models import ComptaOperation
from core.utils import utils_dates


def Generer_pdf(request):
    # 1. Initialisation et validation
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        return JsonResponse({"erreur": "Paramètres invalides"}, status=400)

    options = form.cleaned_data
    date_debut = utils_dates.ConvertDateENGtoDate(options["periode"].split(";")[0])
    date_fin = utils_dates.ConvertDateENGtoDate(options["periode"].split(";")[1])

    compte = options["compte"]
    operations = ComptaOperation.objects.filter(
        compte=compte,
        date__gte=date_debut,
        date__lte=date_fin,
        document__isnull=False
    ).exclude(document='').order_by('num_piece')

    if not operations:
        return JsonResponse({"erreur": "Aucun document trouvé pour cette période."}, status=404)

    writer = PdfWriter()
    largeur, hauteur = A4

    # --- ÉTAPE 1 : GÉNÉRATION DE LA PAGE DE GARDE ---
    buffer_garde = io.BytesIO()
    c = canvas.Canvas(buffer_garde, pagesize=A4)

    # Header style pro (Bleu Sacadoc/Flambeaux)
    c.setFillColor(colors.HexColor("#1d3557"))
    c.rect(0, hauteur - 120, largeur, 120, fill=1, stroke=0)

    c.setStrokeColor(colors.white)
    c.setLineWidth(2)
    c.line(50, hauteur - 85, largeur - 50, hauteur - 85)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(largeur / 2, hauteur - 70, "Recueil des Justificatifs")

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(largeur / 2, hauteur - 160, f"Compte : {compte.nom} (ID: {compte.idcompte})")

    c.setFont("Helvetica", 12)
    structure_nom = compte.structure.nom if compte.structure else ""
    c.drawCentredString(largeur / 2, hauteur - 185, f"Structure : {structure_nom}")
    c.drawCentredString(largeur / 2, hauteur - 205,
                        f"Période : {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}")

    c.showPage()
    c.save()
    writer.add_page(PdfReader(io.BytesIO(buffer_garde.getvalue())).pages[0])

    # --- ÉTAPE 2 : TRAITEMENT DES PIÈCES JOINTES ---
    for op in operations:
        doc_name = op.document.name.lower()
        full_path = default_storage.path(op.document.name)

        # A. Création du bandeau (utilisé pour tamponner les PDF ou habiller les images)
        buffer_header = io.BytesIO()
        can = canvas.Canvas(buffer_header, pagesize=A4)

        # Dessin du bandeau gris en haut
        can.setFillColor(colors.HexColor("#f1f1f1"))
        can.rect(0, hauteur - 50, largeur, 50, fill=1, stroke=0)
        can.setFillColor(colors.black)
        can.setFont("Helvetica-Bold", 11)
        can.drawString(30, hauteur - 30, f"PIÈCE N°{op.num_piece} - {op.date.strftime('%d/%m/%Y')}")
        can.setFont("Helvetica", 10)
        can.drawRightString(largeur - 30, hauteur - 30, f"{op.libelle[:60]}")

        # Cas 1 : Le document est une IMAGE
        if doc_name.endswith(('.jpg', '.jpeg', '.png', '.gif')):
            try:
                img = Image.open(full_path)
                img = ImageOps.exif_transpose(img)  # Gère la rotation auto (smartphone)

                img_w, img_h = img.size
                max_w, max_h = largeur - 60, hauteur - 110
                ratio = min(max_w / img_w, max_h / img_h)
                new_w, new_h = img_w * ratio, img_h * ratio

                x_pos = (largeur - new_w) / 2
                y_pos = (hauteur - 65 - new_h) / 2  # Centré verticalement sous le bandeau

                # On dessine l'image sur le MÊME canvas que le bandeau
                can.drawImage(full_path, x_pos, y_pos, width=new_w, height=new_h, preserveAspectRatio=True)
                can.showPage()
                can.save()
                writer.add_page(PdfReader(io.BytesIO(buffer_header.getvalue())).pages[0])
            except Exception as e:
                print(f"Erreur traitement image {op.num_piece}: {e}")

        # Cas 2 : Le document est un PDF
        elif doc_name.endswith('.pdf'):
            try:
                # On finalise le bandeau seul sur sa page (transparente)
                can.showPage()
                can.save()
                header_reader = PdfReader(io.BytesIO(buffer_header.getvalue()))
                header_page = header_reader.pages[0]

                # Lecture du justificatif PDF
                with open(full_path, 'rb') as f:
                    justif_pdf = PdfReader(f)
                    for i, page in enumerate(justif_pdf.pages):
                        if i == 0:
                            # On fusionne le bandeau PAR-DESSUS la première page
                            page.merge_page(header_page)
                        writer.add_page(page)
            except Exception as e:
                print(f"Erreur traitement PDF {op.num_piece}: {e}")

    # --- ÉTAPE 3 : FINALISATION ET ENREGISTREMENT ---
    final_buffer = io.BytesIO()
    writer.write(final_buffer)

    repertoire = "justifs_compta"
    filename = f"{repertoire}/Recueil_Justificatifs_{compte.idcompte}_{date_debut.strftime('%Y%m%d')}.pdf"

    if default_storage.exists(filename):
        default_storage.delete(filename)

    file_path = default_storage.save(filename, ContentFile(final_buffer.getvalue()))

    return JsonResponse({"nom_fichier": file_path, "status": "success"})

class View(CustomView, TemplateView):
    menu_code = "edition_justifs"
    template_name = "comptabilite/edition_justifs.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Edition PDF des justificatifs"
        context['box_titre'] = ""
        context['box_introduction'] = "Renseignez les paramètres et cliquez sur le bouton Générer le PDF. La génération du document peut nécessiter quelques instants d'attente."
        if "form" not in kwargs:
            context['form'] = Formulaire(request=self.request)
        return context
