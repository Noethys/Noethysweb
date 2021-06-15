# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import decimal


def FloatToDecimal(montant=0.0, plusProche=False):
    """ Transforme un float en decimal """
    if montant == None :
        montant = 0.0
    if type(montant) == str:
        montant = float(montant)
    x = decimal.Decimal(u"%.2f" % montant)
    # Arrondi au centime le plus proche
    if plusProche == True :
        x.quantize(decimal.Decimal('0.01')) # typeArrondi = decimal.ROUND_UP ou decimal.ROUND_DOWN
    return x



if __name__ == "__main__":
    print(FloatToDecimal(3.1359, plusProche=True))
