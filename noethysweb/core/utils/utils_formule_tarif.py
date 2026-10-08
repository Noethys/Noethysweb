# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

"""
Évaluateur de formules de tarifs (méthode de calcul "formule").

Syntaxe façon tableur français :
    SI(VACANCES; TRANCHE(QF; 600; 8; 1000; 12; 15); 6) * SI(RANG_ENFANT >= 2; 0,9; 1)

Sécurité : la formule n'est JAMAIS passée à eval() ou compile(). Elle est
découpée par un tokenizer strict, convertie en expression Python, analysée avec
ast.parse() puis évaluée nœud par nœud par un interpréteur qui n'accepte qu'une
liste blanche de nœuds, de variables et de fonctions.
"""

import ast, re, copy, decimal
from functools import lru_cache


# Variables disponibles : code -> description (affichée dans l'éditeur)
VARIABLES = {
    "QF": "Quotient familial de la famille à la date de la consommation (999999 si la famille n'a pas de QF)",
    "QF_CONNU": "1 si la famille a un QF valide à la date, sinon 0",
    "AGE": "Âge de l'individu en années révolues à la date de la consommation (0 si date de naissance inconnue)",
    "DUREE": "Durée totale des consommations en heures décimales (ex : 3,5 = 3h30)",
    "HEURE_DEBUT": "Heure de début la plus tôt en heures décimales (ex : 13,5 = 13h30)",
    "HEURE_FIN": "Heure de fin la plus tardive en heures décimales",
    "RANG_ENFANT": "Rang de l'individu parmi les membres de la famille inscrits à l'activité, du plus âgé au plus jeune (1, 2, 3...)",
    "NB_ENFANTS_INSCRITS": "Nombre de membres de la famille inscrits à l'activité à la date",
    "JOUR_SEMAINE": "Jour de la semaine (1 = lundi ... 7 = dimanche)",
    "MOIS": "Mois de la consommation (1 à 12)",
    "VACANCES": "1 si la date est pendant les vacances scolaires, sinon 0",
}

# Fonctions disponibles : code -> (syntaxe, description, nbre_args_min, nbre_args_max ou None)
FONCTIONS = {
    "SI": ("SI(condition; valeur_si_vrai; valeur_si_faux)", "Renvoie une valeur ou l'autre selon la condition", 3, 3),
    "TRANCHE": ("TRANCHE(valeur; max1; montant1; max2; montant2; ...; montant_défaut)", "Renvoie le montant de la première tranche dont le maximum est supérieur ou égal à la valeur", 4, None),
    "CHOISIR": ("CHOISIR(index; valeur1; valeur2; ...)", "Renvoie la valeur correspondant à l'index (ex : CHOISIR(JOUR_SEMAINE; ...))", 2, None),
    "ENTRE": ("ENTRE(valeur; min; max)", "Renvoie 1 si la valeur est comprise entre min et max inclus", 3, 3),
    "MIN": ("MIN(valeur1; valeur2; ...)", "Renvoie la plus petite valeur", 1, None),
    "MAX": ("MAX(valeur1; valeur2; ...)", "Renvoie la plus grande valeur", 1, None),
    "ARRONDI": ("ARRONDI(valeur; décimales)", "Arrondit au plus proche", 1, 2),
    "ARRONDI_SUP": ("ARRONDI_SUP(valeur; décimales)", "Arrondit à la valeur supérieure", 1, 2),
    "ARRONDI_INF": ("ARRONDI_INF(valeur; décimales)", "Arrondit à la valeur inférieure", 1, 2),
    "QUESTIONNAIRE": ("QUESTIONNAIRE(id_question)", "Renvoie la réponse numérique à une question des questionnaires famille ou individu", 1, 1),
}

# Exemples affichés dans l'éditeur : (thème, titre, description, formule). Tous sont vérifiés par les tests.
EXEMPLES = [
    # Quotient familial
    ("Quotient familial", "Barème par tranches de QF", "QF ≤ 450 : 3,50 € · ≤ 700 : 5 € · ≤ 1000 : 7 € · au-delà : 9 €.", "TRANCHE(QF; 450; 3,50; 700; 5; 1000; 7; 9)"),
    ("Quotient familial", "Barème fin à 6 tranches", "Six tranches de QF, de 2 € à 9 €.", "TRANCHE(QF; 300; 2; 500; 3; 700; 4,50; 900; 6; 1200; 7,50; 9)"),
    ("Quotient familial", "Taux d'effort", "Tarif proportionnel au QF (1,2 %). À combiner avec un plancher et un plafond.", "QF * 0,012"),
    ("Quotient familial", "Taux d'effort encadré", "1 % du QF, minimum 2 €, maximum 15 €, directement dans la formule.", "MAX(2; MIN(QF * 0,01; 15))"),
    ("Quotient familial", "Taux d'effort différent par tranche", "0,8 % du QF jusqu'à 600, 1 % jusqu'à 1000, 1,2 % au-delà.", "QF * TRANCHE(QF; 600; 0,008; 1000; 0,01; 0,012)"),
    ("Quotient familial", "Tarif linéaire entre deux bornes", "3 € pour un QF de 400 ou moins, 12 € à partir de 1400, progression continue entre les deux.", "MIN(MAX(3 + (QF - 400) * 9 / 1000; 3); 12)"),
    ("Quotient familial", "Remise fixe sous un seuil", "Tarif de 10 €, réduit de 3 € pour les QF inférieurs à 500.", "10 - SI(QF < 500; 3; 0)"),
    ("Quotient familial", "Gratuité pour les plus bas QF", "Gratuit jusqu'à un QF de 300, puis barème à deux tranches.", "SI(QF <= 300; 0; TRANCHE(QF; 800; 5; 8))"),
    ("Quotient familial", "Tarif spécifique sans QF", "Les familles sans QF valide paient 10 € au lieu de la tranche la plus haute.", "SI(QF_CONNU; TRANCHE(QF; 600; 4; 1000; 6; 8); 10)"),
    # Vacances
    ("Vacances", "Tarif vacances / hors vacances", "14 € pendant les vacances scolaires, 6 € en période scolaire.", "SI(VACANCES; 14; 6)"),
    ("Vacances", "Deux barèmes QF selon la période", "Une grille de tranches pour les vacances, une autre pour les mercredis et le périscolaire.", "SI(VACANCES; TRANCHE(QF; 600; 8; 1000; 12; 15); TRANCHE(QF; 600; 4; 1000; 6; 8))"),
    ("Vacances", "Majoration vacances en pourcentage", "Même barème toute l'année, majoré de 20 % pendant les vacances.", "TRANCHE(QF; 700; 5; 8) * SI(VACANCES; 1,2; 1)"),
    ("Vacances", "Vacances d'été, autres vacances, scolaire", "16 € l'été, 13 € les autres vacances, 7 € en période scolaire.", "SI(VACANCES ET ENTRE(MOIS; 7; 8); 16; SI(VACANCES; 13; 7))"),
    # Fratrie
    ("Fratrie", "Réduction à partir du 2e enfant", "−10 % pour le 2e enfant inscrit et les suivants.", "TRANCHE(QF; 700; 6; 10) * SI(RANG_ENFANT >= 2; 0,9; 1)"),
    ("Fratrie", "Réduction progressive par rang", "1er : plein tarif · 2e : −10 % · 3e : −20 % · 4e et suivants : −30 %.", "TRANCHE(QF; 700; 6; 10) * CHOISIR(RANG_ENFANT; 1; 0,9; 0,8; 0,7)"),
    ("Fratrie", "Gratuité à partir du 4e enfant", "Barème QF normal, gratuit dès le 4e enfant inscrit.", "SI(RANG_ENFANT >= 4; 0; TRANCHE(QF; 700; 6; 10))"),
    ("Fratrie", "Remise fixe par enfant supplémentaire", "8 € pour le 1er enfant, 1,50 € de moins par enfant suivant, minimum 3 €.", "MAX(8 - (RANG_ENFANT - 1) * 1,50; 3)"),
    ("Fratrie", "Tarif famille nombreuse", "4 € par enfant si la famille a au moins 3 inscrits, sinon 5 €.", "SI(NB_ENFANTS_INSCRITS >= 3; 4; 5)"),
    ("Fratrie", "Réduction selon la taille de la famille", "Tous les enfants : −5 % pour 2 inscrits, −10 % à partir de 3.", "TRANCHE(QF; 700; 6; 10) * TRANCHE(NB_ENFANTS_INSCRITS; 1; 1; 2; 0,95; 0,9)"),
    # Durée et horaires
    ("Durée et horaires", "Demi-journée ou journée", "6 € jusqu'à 4 h de présence, 10 € au-delà.", "SI(DUREE <= 4; 6; 10)"),
    ("Durée et horaires", "Tranches de durée", "Jusqu'à 2 h : 3 € · 4 h : 5 € · 6 h : 8 € · au-delà : 10 €.", "TRANCHE(DUREE; 2; 3; 4; 5; 6; 8; 10)"),
    ("Durée et horaires", "Facturation à l'heure entamée", "Toute heure commencée est due, à 2 € de l'heure.", "ARRONDI_SUP(DUREE) * 2"),
    ("Durée et horaires", "Facturation à la demi-heure entamée", "Toute demi-heure commencée est due, à 1,80 € la demi-heure.", "ARRONDI_SUP(DUREE * 2) / 2 * 1,80"),
    ("Durée et horaires", "Facturation au quart d'heure selon QF", "Quart d'heure entamé dû, taux horaire de 1,40 € ou 2 € selon le QF.", "ARRONDI_SUP(DUREE * 4) / 4 * TRANCHE(QF; 700; 1,40; 2)"),
    ("Durée et horaires", "Taux horaire selon QF, plafonné", "Prix horaire selon la tranche de QF, plafonné à 12 € par jour.", "MIN(DUREE * TRANCHE(QF; 600; 1,20; 1000; 1,60; 2); 12)"),
    ("Durée et horaires", "Plafond journalier selon QF", "1,50 € de l'heure, sans dépasser 8 € ou 12 € par jour selon le QF.", "MIN(DUREE * 1,50; TRANCHE(QF; 700; 8; 12))"),
    ("Durée et horaires", "Forfait et dépassement", "Forfait de 5 € pour 3 h, puis 2 € par heure supplémentaire.", "5 + MAX(DUREE - 3; 0) * 2"),
    ("Durée et horaires", "Majoration après 18h30", "3 € de base, +5 € si l'enfant part après 18h30.", "SI(HEURE_FIN > 18,5; 5; 0) + 3"),
    ("Durée et horaires", "Supplément arrivée matinale", "1,50 € de l'heure, +2 € si l'enfant arrive avant 8h00.", "SI(HEURE_DEBUT < 8; 2; 0) + DUREE * 1,50"),
    # Âge
    ("Âge", "Tarif moins de 6 ans", "5 € pour les moins de 6 ans, 7 € pour les autres.", "SI(AGE < 6; 5; 7)"),
    ("Âge", "Tranches d'âge", "Jusqu'à 5 ans : 4 € · 6-11 ans : 6 € · 12 ans et plus : 8 €.", "TRANCHE(AGE; 5; 4; 11; 6; 8)"),
    ("Âge", "Gratuité des moins de 3 ans", "Gratuit avant 3 ans, 6 € ensuite.", "SI(AGE < 3; 0; 6)"),
    ("Âge", "Réduction adolescents", "Barème QF avec −20 % à partir de 14 ans.", "TRANCHE(QF; 700; 6; 10) * SI(AGE >= 14; 0,8; 1)"),
    # Calendrier
    ("Calendrier", "Prix par jour de la semaine", "Lun, mar, jeu, ven : 5 € · mercredi : 9 € · samedi, dimanche : 12 €.", "CHOISIR(JOUR_SEMAINE; 5; 5; 9; 5; 5; 12; 12)"),
    ("Calendrier", "Mercredi en période scolaire", "8 € le mercredi hors vacances, 6 € les autres jours.", "SI(JOUR_SEMAINE = 3 ET NON VACANCES; 8; 6)"),
    ("Calendrier", "Lundi et vendredi réduits", "4 € le lundi et le vendredi, 6 € les autres jours.", "SI(JOUR_SEMAINE = 1 OU JOUR_SEMAINE = 5; 4; 6)"),
    ("Calendrier", "Week-end majoré", "Barème QF, +2 € le samedi et le dimanche.", "TRANCHE(QF; 700; 6; 10) + SI(JOUR_SEMAINE >= 6; 2; 0)"),
    ("Calendrier", "Tarif été", "15 € en juillet et août, 12 € le reste de l'année.", "SI(ENTRE(MOIS; 7; 8); 15; 12)"),
    ("Calendrier", "Tarif différent pour chaque mois", "10 € en général, 14 € en juillet-août, 12 € en décembre.", "CHOISIR(MOIS; 10; 10; 10; 10; 10; 10; 14; 14; 10; 10; 10; 12)"),
    # Questionnaire
    ("Questionnaire", "Montant saisi dans un questionnaire", "Utilise la réponse numérique à la question n°12 (remplacez 12 par l'ID de votre question).", "QUESTIONNAIRE(12)"),
    ("Questionnaire", "Pourcentage personnalisé du QF", "Taux d'effort propre à chaque famille, saisi en % dans la question n°12.", "QF * QUESTIONNAIRE(12) / 100"),
    ("Questionnaire", "Supplément saisi par famille", "Barème QF + supplément éventuel saisi dans la question n°15 (option, transport...).", "TRANCHE(QF; 700; 6; 10) + QUESTIONNAIRE(15)"),
    ("Questionnaire", "Tarif imposé ou barème par défaut", "Si un montant est saisi dans la question n°12 il est appliqué, sinon le barème QF.", "SI(QUESTIONNAIRE(12) > 0; QUESTIONNAIRE(12); TRANCHE(QF; 700; 6; 10))"),
    ("Questionnaire", "Coefficient individuel", "Barème QF multiplié par un coefficient saisi dans la question n°12 (1 si vide).", "TRANCHE(QF; 700; 6; 10) * SI(QUESTIONNAIRE(12) > 0; QUESTIONNAIRE(12); 1)"),
    # Arrondis
    ("Arrondis", "Arrondi à l'euro", "Taux d'effort arrondi à l'euro le plus proche.", "ARRONDI(QF * 0,011)"),
    ("Arrondis", "Arrondi aux 10 centimes inférieurs", "Taux d'effort arrondi au dixième d'euro inférieur.", "ARRONDI_INF(QF * 0,011; 1)"),
    ("Arrondis", "Arrondi aux 50 centimes", "Taux d'effort arrondi aux 50 centimes les plus proches.", "ARRONDI(QF * 0,011 * 2) / 2"),
    ("Arrondis", "Arrondi aux 50 centimes supérieurs", "Taux d'effort arrondi aux 50 centimes supérieurs.", "ARRONDI_SUP(QF * 0,011 * 2) / 2"),
    # Combinaisons
    ("Combinaisons", "Cantine maternelle / élémentaire", "Deux barèmes QF : un pour les moins de 6 ans, un pour les autres.", "SI(AGE < 6; TRANCHE(QF; 600; 2,50; 4); TRANCHE(QF; 600; 3; 4,80))"),
    ("Combinaisons", "Périscolaire matin et soir", "1,50 € si arrivée avant 8h45, +1 € par demi-heure entamée après 16h30.", "SI(HEURE_DEBUT < 8,75; 1,50; 0) + SI(HEURE_FIN > 16,5; ARRONDI_SUP((HEURE_FIN - 16,5) * 2); 0)"),
    ("Combinaisons", "Réduction fratrie arrondie", "−15 % dès le 2e enfant, arrondi au dixième d'euro.", "ARRONDI(TRANCHE(QF; 600; 8; 12) * SI(RANG_ENFANT >= 2; 0,85; 1); 1)"),
    ("Combinaisons", "Fratrie et âge avec plancher", "−20 % dès le 2e enfant, −1 € pour les moins de 6 ans, jamais moins de 2 €.", "MAX(TRANCHE(QF; 700; 6; 10) * SI(RANG_ENFANT >= 2; 0,8; 1) - SI(AGE < 6; 1; 0); 2)"),
    ("Combinaisons", "Journée longue en vacances", "Vacances > 5 h : barème journée · vacances ≤ 5 h : barème demi-journée · hors vacances : 4 €.", "SI(VACANCES ET DUREE > 5; TRANCHE(QF; 800; 10; 16); SI(VACANCES; TRANCHE(QF; 800; 6; 9); 4))"),
    # Formules avancées (présentées sur plusieurs lignes : les retours à la ligne et l'indentation sont ignorés au calcul)
    ("Formules avancées", "Barème ALSH complet",
     "Deux barèmes à 5 tranches (vacances / période scolaire), tarif fixe pour les familles sans QF, puis −10 % pour le 2e enfant et −20 % à partir du 3e.",
     "SI(QF_CONNU = 0;\n    SI(VACANCES; 18; 9);\n    SI(VACANCES;\n        TRANCHE(QF; 400; 4; 700; 7; 1000; 10; 1400; 13; 16);\n        TRANCHE(QF; 400; 2; 700; 3,50; 1000; 5; 1400; 6,50; 8)))\n* CHOISIR(RANG_ENFANT; 1; 0,9; 0,8)"),
    ("Formules avancées", "Taux d'effort horaire selon la taille de la famille",
     "Prix horaire = QF × taux (0,06 % pour 1 enfant, 0,05 % pour 2, 0,04 % pour 3, 0,03 % au-delà), encadré entre 0,40 € et 3 € de l'heure, multiplié par la durée.",
     "ARRONDI(\n    DUREE * MIN(MAX(QF * CHOISIR(NB_ENFANTS_INSCRITS; 0,0006; 0,0005; 0,0004; 0,0003); 0,40); 3);\n    2)"),
    ("Formules avancées", "Périscolaire matin, soir et pénalité de retard",
     "Matin avant 8h30 : forfait selon QF · soir après 16h30 : demi-heure entamée selon QF, comptée jusqu'à 18h30 · départ après 18h45 : pénalité de 10 €.",
     "SI(HEURE_DEBUT < 8,5; TRANCHE(QF; 700; 1; 1,50); 0)\n+ SI(HEURE_FIN > 16,5;\n    ARRONDI_SUP((MIN(HEURE_FIN; 18,5) - 16,5) * 2) * TRANCHE(QF; 700; 0,60; 0,90);\n    0)\n+ SI(HEURE_FIN > 18,75; 10; 0)"),
    ("Formules avancées", "Demi-journée, journée ou journée étendue selon QF",
     "Le format est déduit de la durée de présence (≤ 4h30, ≤ 7 h, au-delà), chacun avec son propre barème QF.",
     "TRANCHE(DUREE;\n    4,5; TRANCHE(QF; 700; 4; 6);\n    7;   TRANCHE(QF; 700; 6; 9);\n         TRANCHE(QF; 700; 8; 12))"),
    ("Formules avancées", "Prix horaire dégressif par paliers",
     "Les 2 premières heures à 2 €, les 2 suivantes à 1,50 €, les heures au-delà de 4 h à 1 €.",
     "MIN(DUREE; 2) * 2\n+ MIN(MAX(DUREE - 2; 0); 2) * 1,50\n+ MAX(DUREE - 4; 0) * 1"),
    ("Formules avancées", "Franchise de 30 minutes et plafond selon QF",
     "La première demi-heure est gratuite, puis chaque demi-heure entamée est facturée selon le QF, avec un plafond journalier lui aussi selon le QF.",
     "MIN(\n    ARRONDI_SUP(MAX(DUREE - 0,5; 0) * 2) * TRANCHE(QF; 700; 0,75; 1,10);\n    TRANCHE(QF; 700; 6; 9))"),
    ("Formules avancées", "Mercredi découpé en matin, repas et après-midi",
     "Les créneaux sont déduits des horaires (matin si arrivée avant 12h, repas si présent de 12h à 13h30, après-midi si départ après 13h30), puis pondérés par un coefficient de QF.",
     "(SI(HEURE_DEBUT < 12; 4; 0)\n + SI(HEURE_DEBUT < 12 ET HEURE_FIN > 13,5; 3,50; 0)\n + SI(HEURE_FIN > 13,5; 4; 0))\n* TRANCHE(QF; 600; 0,6; 1000; 0,8; 1)"),
    ("Formules avancées", "Tarif linéaire, fratrie et arrondi supérieur",
     "2 € pour un QF de 300 ou moins, +1 centime par point de QF, plafonné à 14 €, −15 % dès le 2e enfant, arrondi aux 10 centimes supérieurs.",
     "ARRONDI_SUP(\n    MIN(MAX(2 + (QF - 300) * 0,01; 2); 14)\n    * SI(RANG_ENFANT >= 2; 0,85; 1);\n    1)"),
    ("Formules avancées", "Stage sportif selon l'âge, l'été et le week-end",
     "Barème QF différent avant et après 8 ans, supplément de 2 € l'été pour les plus grands, majoration de 25 % le week-end.",
     "SI(AGE < 8;\n    TRANCHE(QF; 800; 6; 9);\n    TRANCHE(QF; 800; 8; 12) + SI(ENTRE(MOIS; 7; 8); 2; 0))\n* SI(JOUR_SEMAINE >= 6; 1,25; 1)"),
    ("Formules avancées", "Taux d'effort, période et famille nombreuse",
     "Taux d'effort de 1,5 % en vacances et 0,8 % en période scolaire, −15 % pour 3 inscrits et −25 % au-delà, avec plancher et plafond propres à chaque période.",
     "MAX(\n    MIN(\n        QF * SI(VACANCES; 0,015; 0,008) * TRANCHE(NB_ENFANTS_INSCRITS; 2; 1; 3; 0,85; 0,75);\n        SI(VACANCES; 18; 9));\n    SI(VACANCES; 3; 1,50))"),
    ("Formules avancées", "Tarification solidaire",
     "Gratuit pour les moins de 6 ans des familles au QF ≤ 300 · 2 € pour les QF ≤ 500 · barème sinon · −20 % pour le 2e enfant, −40 % à partir du 3e.",
     "SI(QF_CONNU ET QF <= 300 ET AGE < 6;\n    0;\n    SI(QF_CONNU ET QF <= 500; 2; TRANCHE(QF; 900; 4; 6))\n    * CHOISIR(RANG_ENFANT; 1; 0,8; 0,6))"),
    ("Formules avancées", "Coefficient par jour selon la période",
     "Barème QF multiplié par un coefficient par jour : mercredi majoré de 50 % hors vacances seulement, week-end majoré de 30 %.",
     "TRANCHE(QF; 700; 5; 8)\n* CHOISIR(JOUR_SEMAINE;\n    1; 1; SI(VACANCES; 1; 1,5); 1; 1; 1,3; 1,3)"),
    ("Formules avancées", "Tarif imposé avec garde-fous",
     "Le montant saisi dans la question n°12 est appliqué, ramené entre 1 € et 20 € ; sans réponse, barème QF avec réduction fratrie.",
     "SI(QUESTIONNAIRE(12) > 0;\n    MIN(MAX(QUESTIONNAIRE(12); 1); 20);\n    TRANCHE(QF; 600; 5; 1000; 8; 11) * SI(RANG_ENFANT >= 2; 0,9; 1))"),
    ("Formules avancées", "Taux d'effort selon la tranche d'âge",
     "0,6 % du QF jusqu'à 5 ans, 0,8 % de 6 à 11 ans, 1 % au-delà, arrondi au dixième et encadré entre 1 € et 12 €.",
     "MIN(MAX(\n    ARRONDI(QF * TRANCHE(AGE; 5; 0,006; 11; 0,008; 0,01); 1);\n    1); 12)"),
    ("Formules avancées", "Journée de séjour : QF, été, fratrie et familles sans QF",
     "Prix de journée à 4 tranches de QF, +5 € l'été, −10 % pour 2 inscrits et −20 % au-delà, +10 % sans QF connu, arrondi à l'euro.",
     "ARRONDI(\n    (TRANCHE(QF; 500; 20; 800; 28; 1200; 36; 45)\n     + SI(ENTRE(MOIS; 7; 8); 5; 0))\n    * TRANCHE(NB_ENFANTS_INSCRITS; 1; 1; 2; 0,9; 0,8)\n    * SI(QF_CONNU; 1; 1,1);\n    0)"),
]

LONGUEUR_MAX = 2000
NBRE_NOEUDS_MAX = 400
ZERO, UN = decimal.Decimal(0), decimal.Decimal(1)


class ErreurFormule(Exception):
    """ Erreur de syntaxe ou d'évaluation, avec un message destiné à l'utilisateur """
    pass


# ---------------------------------------------------------------------------
# Tokenizer : syntaxe française -> source Python
# ---------------------------------------------------------------------------

_REGEX_TOKENS = re.compile(r"""
    (?P<espace>\s+)
  | (?P<nombre>\d+(?:[.,]\d+)?)
  | (?P<ident>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op><=|>=|<>|!=|==|[-+*/();<>=])
""", re.VERBOSE)

_TRADUCTION_OPS = {";": ",", "=": "==", "<>": "!=", "==": "==", "!=": "!="}
_TRADUCTION_MOTS = {"ET": "and", "OU": "or", "NON": "not"}


def _Traduire(texte):
    elements = []
    position = 0
    while position < len(texte):
        match = _REGEX_TOKENS.match(texte, position)
        if not match:
            raise ErreurFormule("Caractère non autorisé « %s » en position %d" % (texte[position], position + 1))
        position = match.end()
        if match.lastgroup == "espace":
            continue
        valeur = match.group()
        if match.lastgroup == "nombre":
            elements.append(valeur.replace(",", "."))
        elif match.lastgroup == "ident":
            valeur = valeur.upper()
            elements.append(_TRADUCTION_MOTS.get(valeur, valeur))
        else:
            elements.append(_TRADUCTION_OPS.get(valeur, valeur))
    if not elements:
        raise ErreurFormule("La formule est vide")
    return " ".join(elements)


# ---------------------------------------------------------------------------
# Analyse et validation (liste blanche)
# ---------------------------------------------------------------------------

_NOEUDS_AUTORISES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.Call, ast.Name, ast.Load, ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
)


class FormuleTarif:
    """ Formule analysée et validée, réutilisable pour de nombreuses évaluations """

    def __init__(self, texte):
        if not texte or not texte.strip():
            raise ErreurFormule("La formule est vide")
        if len(texte) > LONGUEUR_MAX:
            raise ErreurFormule("La formule ne doit pas dépasser %d caractères" % LONGUEUR_MAX)
        self.texte = texte
        source = _Traduire(texte)
        try:
            self.arbre = ast.parse(source, mode="eval")
        except SyntaxError:
            raise ErreurFormule("Syntaxe incorrecte : vérifiez les parenthèses, les points-virgules et les opérateurs")
        except (RecursionError, MemoryError, ValueError):
            raise ErreurFormule("La formule est trop complexe")
        self.variables = set()
        self._Valider()

    def _Valider(self):
        noeuds = list(ast.walk(self.arbre))
        if len(noeuds) > NBRE_NOEUDS_MAX:
            raise ErreurFormule("La formule est trop complexe")
        fonctions_appelees = {id(noeud.func) for noeud in noeuds if isinstance(noeud, ast.Call)}

        for noeud in noeuds:
            if not isinstance(noeud, _NOEUDS_AUTORISES):
                raise ErreurFormule("Élément non autorisé dans la formule")

            if isinstance(noeud, ast.Constant) and (isinstance(noeud.value, bool) or not isinstance(noeud.value, (int, float))):
                raise ErreurFormule("Valeur non autorisée dans la formule")

            if isinstance(noeud, ast.Call):
                if not isinstance(noeud.func, ast.Name) or noeud.func.id not in FONCTIONS:
                    nom = noeud.func.id if isinstance(noeud.func, ast.Name) else "?"
                    raise ErreurFormule("Fonction inconnue : %s" % nom)
                if noeud.keywords:
                    raise ErreurFormule("Syntaxe incorrecte dans %s()" % noeud.func.id)
                syntaxe, description, nbre_min, nbre_max = FONCTIONS[noeud.func.id]
                nbre = len(noeud.args)
                if nbre < nbre_min or (nbre_max is not None and nbre > nbre_max):
                    raise ErreurFormule("Nombre de paramètres incorrect pour %s. Syntaxe : %s" % (noeud.func.id, syntaxe))
                if noeud.func.id == "TRANCHE" and nbre % 2 != 0:
                    raise ErreurFormule("TRANCHE attend des paires maximum/montant suivies d'un montant par défaut. Syntaxe : %s" % syntaxe)
                if noeud.func.id == "QUESTIONNAIRE":
                    arg = noeud.args[0]
                    if not (isinstance(arg, ast.Constant) and isinstance(arg.value, int) and not isinstance(arg.value, bool)):
                        raise ErreurFormule("QUESTIONNAIRE attend le numéro (ID) d'une question, ex : QUESTIONNAIRE(12)")

            if isinstance(noeud, ast.Name) and id(noeud) not in fonctions_appelees:
                if noeud.id in FONCTIONS:
                    raise ErreurFormule("La fonction %s doit être suivie de parenthèses" % noeud.id)
                if noeud.id not in VARIABLES:
                    raise ErreurFormule("Variable inconnue : %s" % noeud.id)
                self.variables.add(noeud.id)

    def Get_questions(self):
        """ Renvoie les ID de questions utilisées par la fonction QUESTIONNAIRE """
        return {noeud.args[0].value for noeud in ast.walk(self.arbre) if isinstance(noeud, ast.Call) and noeud.func.id == "QUESTIONNAIRE"}

    # -----------------------------------------------------------------------
    # Évaluation
    # -----------------------------------------------------------------------

    def Evaluer(self, variables=None, fonction_questionnaire=None):
        """
        variables : dict {code: valeur} ou callable(code) -> valeur. Seules les
                    variables utilisées par la formule sont demandées.
        fonction_questionnaire : callable(idquestion) -> valeur numérique
        Renvoie un Decimal.
        """
        # Copie légère : l'instance analysée est partagée via le cache, l'état d'évaluation ne doit pas l'être (threads)
        evaluateur = copy.copy(self)
        evaluateur._cache_variables = {}
        evaluateur._variables = variables or {}
        evaluateur._fonction_questionnaire = fonction_questionnaire
        try:
            with decimal.localcontext() as ctx:
                ctx.prec = 28
                ctx.traps[decimal.DivisionByZero] = True
                ctx.traps[decimal.InvalidOperation] = True
                return evaluateur._Eval(self.arbre.body)
        except decimal.DivisionByZero:
            raise ErreurFormule("Division par zéro")
        except (decimal.InvalidOperation, OverflowError):
            raise ErreurFormule("Calcul impossible (valeur hors limites)")
        except RecursionError:
            raise ErreurFormule("La formule est trop complexe")

    def _Get_variable(self, code):
        if code not in self._cache_variables:
            if callable(self._variables):
                valeur = self._variables(code)
            else:
                if code not in self._variables:
                    raise ErreurFormule("La variable %s n'est pas disponible" % code)
                valeur = self._variables[code]
            self._cache_variables[code] = _Decimal(valeur, code)
        return self._cache_variables[code]

    def _Eval(self, noeud):
        if isinstance(noeud, ast.Constant):
            return decimal.Decimal(repr(noeud.value)) if isinstance(noeud.value, float) else decimal.Decimal(noeud.value)

        if isinstance(noeud, ast.Name):
            return self._Get_variable(noeud.id)

        if isinstance(noeud, ast.UnaryOp):
            valeur = self._Eval(noeud.operand)
            if isinstance(noeud.op, ast.USub):
                return -valeur
            if isinstance(noeud.op, ast.UAdd):
                return valeur
            return UN if valeur == 0 else ZERO

        if isinstance(noeud, ast.BinOp):
            gauche, droite = self._Eval(noeud.left), self._Eval(noeud.right)
            if isinstance(noeud.op, ast.Add):
                return gauche + droite
            if isinstance(noeud.op, ast.Sub):
                return gauche - droite
            if isinstance(noeud.op, ast.Mult):
                return gauche * droite
            return gauche / droite

        if isinstance(noeud, ast.BoolOp):
            if isinstance(noeud.op, ast.And):
                return UN if all(self._Eval(valeur) != 0 for valeur in noeud.values) else ZERO
            return UN if any(self._Eval(valeur) != 0 for valeur in noeud.values) else ZERO

        if isinstance(noeud, ast.Compare):
            gauche = self._Eval(noeud.left)
            for operateur, comparateur in zip(noeud.ops, noeud.comparators):
                droite = self._Eval(comparateur)
                ok = {ast.Eq: gauche == droite, ast.NotEq: gauche != droite, ast.Lt: gauche < droite,
                      ast.LtE: gauche <= droite, ast.Gt: gauche > droite, ast.GtE: gauche >= droite}[type(operateur)]
                if not ok:
                    return ZERO
                gauche = droite
            return UN

        if isinstance(noeud, ast.Call):
            return self._Appel(noeud.func.id, noeud.args)

        raise ErreurFormule("Élément non autorisé dans la formule")

    def _Appel(self, nom, args):
        # Évaluation paresseuse pour SI, TRANCHE et CHOISIR (évite par ex. une division par zéro dans une branche non retenue)
        if nom == "SI":
            return self._Eval(args[1]) if self._Eval(args[0]) != 0 else self._Eval(args[2])

        if nom == "TRANCHE":
            valeur = self._Eval(args[0])
            for index in range(1, len(args) - 1, 2):
                if valeur <= self._Eval(args[index]):
                    return self._Eval(args[index + 1])
            return self._Eval(args[-1])

        if nom == "CHOISIR":
            index = int(self._Eval(args[0]))
            index = min(max(index, 1), len(args) - 1)
            return self._Eval(args[index])

        if nom == "QUESTIONNAIRE":
            if not self._fonction_questionnaire:
                return ZERO
            return _Decimal(self._fonction_questionnaire(args[0].value), "QUESTIONNAIRE(%d)" % args[0].value)

        valeurs = [self._Eval(arg) for arg in args]

        if nom == "MIN":
            return min(valeurs)
        if nom == "MAX":
            return max(valeurs)
        if nom == "ENTRE":
            return UN if valeurs[1] <= valeurs[0] <= valeurs[2] else ZERO
        if nom in ("ARRONDI", "ARRONDI_SUP", "ARRONDI_INF"):
            decimales = int(valeurs[1]) if len(valeurs) > 1 else 0
            if not 0 <= decimales <= 6:
                raise ErreurFormule("%s : le nombre de décimales doit être compris entre 0 et 6" % nom)
            arrondi = {"ARRONDI": decimal.ROUND_HALF_UP, "ARRONDI_SUP": decimal.ROUND_CEILING, "ARRONDI_INF": decimal.ROUND_FLOOR}[nom]
            return valeurs[0].quantize(decimal.Decimal(1).scaleb(-decimales), rounding=arrondi)

        raise ErreurFormule("Fonction inconnue : %s" % nom)


def _Decimal(valeur, code=""):
    if valeur is None:
        return ZERO
    if isinstance(valeur, bool):
        return UN if valeur else ZERO
    if isinstance(valeur, decimal.Decimal):
        return valeur
    try:
        return decimal.Decimal(str(valeur).replace(",", "."))
    except decimal.InvalidOperation:
        raise ErreurFormule("La valeur de %s n'est pas un nombre" % code)


@lru_cache(maxsize=256)
def Get_formule(texte):
    """ Analyse une formule avec mise en cache (lève ErreurFormule si invalide) """
    return FormuleTarif(texte)


def Valider_formule(texte):
    """ Renvoie None si la formule est valide, sinon le message d'erreur """
    try:
        Get_formule(texte)
        return None
    except ErreurFormule as err:
        return str(err)
