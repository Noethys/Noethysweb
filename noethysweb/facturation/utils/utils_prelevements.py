# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
import string


def CheckIBAN(iban=""):
    """IBAN Python validation"""
    IBAN_CHAR_MAP = {"A": "10", "B": "11", "C": "12", "D": "13", "E": "14", "F": "15", "G": "16", "H": "17", "I": "18", "J": "19", "K": "20", "L": "21", "M": "22",
                     "N": "23", "O": "24", "P": "25", "Q": "26", "R": "27", "S": "28", "T": "29", "U": "30", "V": "31", "W": "32", "X": "33", "Y": "34", "Z": "35"}
    def replaceAll(text, char_map):
        for k, v in char_map.items():
            text = text.replace(k, v)
        return text
    try:
        iban = iban.replace('-', '').replace(' ', '')
        iban = replaceAll(iban[4:] + iban[0:4], IBAN_CHAR_MAP)
        res = int(iban) % 97
        return res == 1
    except:
        return False

def CheckBIC(bic):
    """ Validation for ISO 9362:2009 (SWIFT-BIC). """
    # Length is 8 or 11.
    swift_bic_length = len(bic)
    if swift_bic_length != 8 and swift_bic_length != 11:
        return False
    # First 4 letters are A - Z.
    for x in bic[:4]:
        if x not in string.ascii_uppercase:
            return False
    return True
