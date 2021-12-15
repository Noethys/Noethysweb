# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
logging.getLogger('PIL').setLevel(logging.WARNING)
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from core.models import Mandat, CompteBancaire
from core.utils import utils_impression


class Impression(utils_impression.Impression):
    def __init__(self, *args, **kwds):
        utils_impression.Impression.__init__(self, *args, **kwds)

    def Draw(self):
        # Importation du mandat
        mandat = Mandat.objects.get(pk=self.dict_donnees["idmandat"])

        # Importation de l'ICS
        compte = CompteBancaire.objects.filter(code_ics__isnull=False).first()
        code_ics = compte.code_ics if compte else "-- ICS non renseigné --"

        # Préparation du document
        styleSheet = getSampleStyleSheet()
        largeurContenu = 500
        dataTableau = []

        # Titre du document
        dataTableau.append([Paragraph(u"""<para align=center fontSize=16><b>Mandat de prélèvement SEPA</b></para>""", styleSheet['BodyText']),])

        # Nom de l'organisateur
        dataTableau.append([[
            Paragraph("""<para align=center fontSize=10>%s</para>""" % self.dict_donnees["{ORGANISATEUR_NOM}"], styleSheet['BodyText']),
            Paragraph("""<para align=center fontSize=10>ICS n°%s</para>""" % code_ics, styleSheet['BodyText']),
            Paragraph("""<para align=center fontSize=8>%s %s %s</para>""" % (self.dict_donnees["{ORGANISATEUR_RUE}"], self.dict_donnees["{ORGANISATEUR_CP}"], self.dict_donnees["{ORGANISATEUR_VILLE}"]), styleSheet['BodyText']),
        ]])

        # Mention légale obligatoire sur le SEPA
        mention_sepa = Paragraph("""
            <para align=left leading=10 fontSize=7>En signant ce mandat, vous autorisez le créancier '%s' à envoyer des instructions à votre banque pour débiter votre compte, et votre banque à débiter votre compte conformément aux instructions du créancier '%s'.
            Vous bénéficiez du droit d'être remboursé par votre banque selon les conditions décrites dans la convention que vous avez passée avec elle.
            Une demande de remboursement doit être présentée dans les 8 semaines suivant la date de débit de votre compte pour un prélèvement autorisé.
            Vos droits concernant le prélèvement sont expliqués dans un document que vous pouvez obtenir auprès de votre banque.
            </para>""" % (self.dict_donnees["{ORGANISATEUR_NOM}"], self.dict_donnees["{ORGANISATEUR_NOM}"]), styleSheet['BodyText'])
        dataTableau.append([mention_sepa,])

        # RUM
        dataTableau.append([Paragraph("<para align=center fontSize=8><b>Référence unique du mandat</b></para>", styleSheet['BodyText']),])
        dataTableauTemp = [[Paragraph("<para align=right fontSize=10>RUM :</para>", styleSheet['BodyText']), self.Cases(modele=[1 for x in range(38)], texte=mandat.rum)], ]
        style = TableStyle([('VALIGN', (0, 0), (-1, -1), "MIDDLE"), ])
        tableauTemp = Table(dataTableauTemp, [100, 400])
        tableauTemp.setStyle(style)
        dataTableau.append([tableauTemp, ])

        # Nom et coordonnées et débiteur
        dataTableau.append([Paragraph("<para align=center fontSize=8><b>Identité et coordonnées du débiteur</b></para>", styleSheet['BodyText']), ])
        dataTableauTemp = [
            [Paragraph("<para align=right fontSize=10>Nom et prénom :</para>", styleSheet['BodyText']), self.Cases(modele=[1 for x in range(38)], texte=mandat.individu_nom or mandat.individu.Get_nom())],
            [Paragraph("<para align=right fontSize=10>Adresse :</para>", styleSheet['BodyText']), self.Cases(modele=[1 for x in range(38)], texte=mandat.individu_rue or mandat.individu.rue_resid)],
            [Paragraph("<para align=right fontSize=10>Code postal :</para>", styleSheet['BodyText']), self.Cases(modele=[1 for x in range(38)], texte=mandat.individu_cp or mandat.individu.cp_resid)],
            [Paragraph("<para align=right fontSize=10>Ville :</para>", styleSheet['BodyText']), self.Cases(modele=[1 for x in range(38)], texte=mandat.individu_ville or mandat.individu.ville_resid)],
        ]
        style = TableStyle([('VALIGN', (0, 0), (-1, -1), "MIDDLE"), ])
        tableauTemp = Table(dataTableauTemp, [100, 400])
        tableauTemp.setStyle(style)
        dataTableau.append([tableauTemp, ])

        # Compte à débiter
        dataTableau.append([Paragraph("<para align=center fontSize=8><b>Compte à débiter</b></para>", styleSheet['BodyText']), ])

        iban = self.Cases(modele=[1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1], texte=mandat.iban)
        bic = self.Cases(modele=[1 for x in range(11)], texte=mandat.bic)
        dataTableauTemp = [
            [Paragraph("<para align=right fontSize=10>IBAN :</para>", styleSheet['BodyText']), iban],
            [Paragraph("<para align=right fontSize=10>BIC :</para>", styleSheet['BodyText']), bic],
        ]
        style = TableStyle([('VALIGN', (0, 0), (-1, -1), "MIDDLE"), ])
        tableauTemp = Table(dataTableauTemp, [100, 400])
        tableauTemp.setStyle(style)
        dataTableau.append([tableauTemp, ])

        # Type de paiement
        dataTableau.append([Paragraph("<para align=center fontSize=8><b>Type de paiement</b></para>", styleSheet['BodyText']), ])

        if mandat.type == "RECURRENT":
            recurrent = "X"
            ponctuel = ""
        else:
            recurrent = ""
            ponctuel = "X"
        dataTableauTemp = ["",
            Paragraph("<para align=left fontSize=10>Paiement récurrent :</para>", styleSheet['BodyText']),
            self.Cases(modele=[1, ], texte=recurrent), "",
            Paragraph("<para align=left fontSize=10>Paiement ponctuel :</para>", styleSheet['BodyText']),
            self.Cases(modele=[1, ], texte=ponctuel),
        ]
        style = TableStyle([('VALIGN', (0, 0), (-1, -1), "MIDDLE"), ('ALIGN', (0, 0), (-1, -1), "CENTER"), ])
        tableauTemp = Table([dataTableauTemp, ], [100, 105, 10, 50, 105, 10])
        tableauTemp.setStyle(style)
        dataTableau.append([tableauTemp, ])

        # Signature
        dataTableau.append([Paragraph("<para align=center fontSize=8><b>Signature</b></para>", styleSheet['BodyText']), ])
        dataTableauTemp = [
            [Paragraph("<para align=right fontSize=10>Fait à :</para>", styleSheet['BodyText']), self.Cases(modele=[1 for x in range(38)])],
            [Paragraph("<para align=right fontSize=10>Le :</para>", styleSheet['BodyText']), self.Cases(modele=[1, 1, 2, 1, 1, 2, 1, 1, 1, 1], texte="  /  /    ")],
            [Paragraph("<para align=right fontSize=10>Signature :</para>", styleSheet['BodyText']), ""], ["", ""],
            ["", ""], ["", ""], ["", ""], ["", ""],
        ]
        style = TableStyle([('VALIGN', (0, 0), (-1, -1), "MIDDLE"), ])
        tableauTemp = Table(dataTableauTemp, [100, 400])
        tableauTemp.setStyle(style)
        dataTableau.append([tableauTemp, ])

        # Mention CNIL
        mention_cnil = Paragraph("""
            <para align=left leading=10 fontSize=7>Les informations contenus dans le présent mandat, qui doit être complété, sont destinés à n'être utilisées par le créancier que pour la gestion
            de sa relation avec son client. Elles pourront donner lieu à l'exercice, par ce dernier, de ses droits d'oppositions, d'accès et de rectifications tels 
            que prévus aux articles 38 et suivants de la loi n°78-17 du 6 janvier 1978 relative à l'informatique, aux fichiers et aux libertés.
            </para>""", styleSheet['BodyText'])
        dataTableau.append([mention_cnil, ])

        # Formatage du tableau principal
        listeStyles = [('GRID', (0, 0), (-1, -1), 0.25, colors.black), ('VALIGN', (0, 0), (-1, -1), "MIDDLE"),
            ('TOPPADDING', (0, 0), (0, 0), 20), ('BOTTOMPADDING', (0, 0), (0, 0), 25), ]
        for ligne in (0, 3, 5, 7, 9, 11):
            listeStyles.append(('BACKGROUND', (0, ligne), (-1, ligne), (0.8, 0.8, 0.8)))
        style = TableStyle(listeStyles)
        tableau = Table(dataTableau, [largeurContenu, ])
        tableau.setStyle(style)
        dataTableau.append(tableau)
        self.story.append(tableau)

    def Cases(self, modele=[1, 1, 1, 0, 1, 1, 1], texte="", largeurColonnes=10, couleur=(0.8, 0.8, 0.8)):
        """
        1 = Case à avec texte avec cadre
        2 = Case avec texte sans cadre
        0 = Case sans texte et sans cadre
        """
        if texte == None: texte = ""
        dataTableau = []
        largeursColonnes = []
        listeStyles = [('VALIGN', (0, 0), (-1, -1), "MIDDLE"), ('ALIGN', (0, 0), (-1, -1), "CENTER"), ]
        indexColonne = 0
        indexTexte = 0
        for code in modele:
            largeursColonnes.append(largeurColonnes)

            if code == 1 or code == 2:
                if len(texte) > indexTexte:
                    dataTableau.append(texte[indexTexte])
                    indexTexte += 1
                else:
                    dataTableau.append("")
                if code == 1:
                    listeStyles.append(('GRID', (indexColonne, 0), (indexColonne, -1), 0.25, couleur))
            else:
                dataTableau.append("")
            indexColonne += 1

        style = TableStyle(listeStyles)
        tableau = Table([dataTableau, ], largeursColonnes)
        tableau.setStyle(style)
        return tableau
