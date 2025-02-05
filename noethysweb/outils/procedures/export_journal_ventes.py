#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime
logger = logging.getLogger(__name__)
from core.models import Prestation
from outils.views.procedures import BaseProcedure
from facturation.utils.utils_export_ecritures import BaseExporter


class Exporter(BaseExporter):
    def Creation_fichier(self, classeur=None):
        # Création du fichier xlsx
        feuille = classeur.add_worksheet("Page 1")
        format_money = classeur.add_format({"num_format": "# ##0.00"})

        # Importation des prestations
        prestations = Prestation.objects.select_related("activite").filter(date__gte=self.options.date_debut, date__lte=self.options.date_fin).order_by("date")

        lignes = []
        for num_ecriture, prestation in enumerate(prestations, 1):
            lignes.append({
                "num_ecriture": num_ecriture,
                "date": prestation.date.strftime("%d%m%y"),
                "code_journal": "VE",
                "compte": "706",
                "label": ("%s - %s" % (prestation.activite.abrege, prestation.label)) if prestation.activite else prestation.label,
                "montant": prestation.montant,
                "sens": "C",
                "monnaie": "EUR",
            })

        # Définition des colonnes
        colonnes = [
            ("num_ecriture", None), ("date", None), ("code_journal", None), ("compte", None), ("vide", None), ("label", None),
            ("vide", None), ("montant", format_money), ("sens", None), ("vide", None), ("monnaie", None),
        ]

        # Remplissage des cases
        for index_ligne, ligne in enumerate(lignes, 1):
            for index_colonne, (code_colonne, format_case) in enumerate(colonnes, 0):
                feuille.write(index_ligne, index_colonne, ligne.get(code_colonne, ""), format_case)

        classeur.close()
        return True


class Procedure(BaseProcedure):
    def Arguments(self, parser=None):
        parser.add_argument("date_debut", type=lambda s: datetime.datetime.strptime(s, "%d/%m/%Y").date())
        parser.add_argument("date_fin", type=lambda s: datetime.datetime.strptime(s, "%d/%m/%Y").date())

    def Executer(self, variables=None):
        export = Exporter(options=variables)
        resultat = export.Generer_xlsx(nom_fichier="export_journal_ventes.xlsx")
        if not resultat:
            return export.Get_erreurs_html()
        self.nom_fichier = resultat
        return "Le fichier a été généré avec succès. Il vous sera proposé au téléchargement dans quelques instants..."
