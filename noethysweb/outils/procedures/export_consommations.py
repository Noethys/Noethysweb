#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime
logger = logging.getLogger(__name__)
from django.db.models import Q
from core.models import Consommation
from core.utils import utils_dates
from outils.views.procedures import BaseProcedure
from facturation.utils.utils_export_ecritures import BaseExporter


class Exporter(BaseExporter):
    def Creation_fichier(self, classeur=None):
        # Création du fichier xlsx
        feuille = classeur.add_worksheet("Page 1")
        format_date = classeur.add_format({"num_format": "DD/MM/YYYY"})
        format_heure = classeur.add_format({"num_format": "hh:mm"})
        format_duree = classeur.add_format({"num_format": "[h]:mm"})

        # Importation des consommations
        conditions = Q(date__gte=self.options.date_debut, date__lte=self.options.date_fin)
        if self.options.idactivite:
            conditions &= Q(activite_id=self.options.idactivite)
        if self.options.etats:
            conditions &= Q(etat__in=self.options.etats.split(";"))
        if self.options.unites:
            conditions &= Q(unite_id__in=[int(idunite) for idunite in self.options.unites.split(";")])
        if self.options.idgroupe:
            conditions &= Q(groupe_id=self.options.idgroupe)
        consommations = Consommation.objects.select_related("individu", "activite").filter(conditions).order_by("date")

        lignes = [{"date": "Date", "individu": "Individu", "age": "Age", "heure_debut": "Début", "heure_fin": "Fin", "duree": "Durée"}]
        for conso in consommations:
            duree = utils_dates.SoustractionHeures(conso.heure_fin, conso.heure_debut) if conso.heure_fin else None
            age = (conso.date.year - conso.individu.date_naiss.year) - int((conso.date.month, conso.date.day) < (conso.individu.date_naiss.month, conso.individu.date_naiss.day)) if conso.individu.date_naiss else None

            # Filtre sur l'âge
            if self.options.age and (not age or not eval("%s%s" % (age, self.options.age))):
                continue

            lignes.append({
                "date": conso.date,
                "individu": conso.individu.Get_nom(),
                "age": age,
                "heure_debut": conso.heure_debut,
                "heure_fin": conso.heure_fin,
                "duree": duree,
            })

        # Définition des colonnes
        colonnes = [
            ("date", format_date), ("individu", None), ("age", None), ("heure_debut", format_heure),
            ("heure_fin", format_heure), ("duree", format_duree),
        ]

        # Remplissage des cases
        for index_ligne, ligne in enumerate(lignes, 0):
            for index_colonne, (code_colonne, format_case) in enumerate(colonnes, 0):
                feuille.write(index_ligne, index_colonne, ligne.get(code_colonne, ""), format_case)

        classeur.close()
        return True


class Procedure(BaseProcedure):
    def Arguments(self, parser=None):
        parser.add_argument("date_debut", type=lambda s: datetime.datetime.strptime(s, "%d/%m/%Y").date())
        parser.add_argument("date_fin", type=lambda s: datetime.datetime.strptime(s, "%d/%m/%Y").date())
        parser.add_argument("--idactivite", type=int, help="ID de l'activité", nargs="?", default=0)
        parser.add_argument("--idgroupe", type=int, help="ID du groupe", nargs="?", default=0)
        parser.add_argument("--etats", type=str, help="Etats", nargs="?", default="reservation;present;absenti;absentj")
        parser.add_argument("--unites", type=str, help="Unités", nargs="?", default="")
        parser.add_argument("--age", type=str, help="Age (Exemples : >6, <=6)", nargs="?", default="")

    def Executer(self, variables=None):
        export = Exporter(options=variables)
        resultat = export.Generer_xlsx(nom_fichier="export_consommations.xlsx")
        if not resultat:
            return export.Get_erreurs_html()
        self.nom_fichier = resultat
        return "Le fichier a été généré avec succès. Il vous sera proposé au téléchargement dans quelques instants..."
