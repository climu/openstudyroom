""" Get data from go Federations"""
from math import log, ceil
import requests
import csv

def get_egf_rank(egf_id):
    """
    Check if an EGF id is valid and get its rank.
    We return the rank (a string) or None if it's not valid
    """
    url = "https://www.europeangodatabase.eu/EGD/GetPlayerDataByPIN.php?pin=" + str(egf_id)
    request = requests.get(url, timeout=10).json()
    if request['retcode'] == "Ok":
        return request['Grade']
    return None

def get_ffg_rank(ffg_licence_number):
    """
    Check if an FFG licence number is valid and get its rank.
    We return the rank (a string) or None if it's not valid
    """
    url = "https://ffg.jeudego.org/echelle/echtxt/echelle.txt"
    request = requests.get(url, timeout=10)
    if request.status_code == 200:
        #1400315 HWANG In-seong            720        38Gr
        #1800104 PORTEJOIE-KALINCHENKO Gu-2950        44Na
        #2100088 ABIASSI Samuel             NC        38Gr
        #0123456789012345678901234567890123456789
        line = None
        # get first line starting with licence number.
        # we skip 3 first lines that are headers
        for l in request.text.splitlines()[3:]:
            if l.startswith(str(ffg_licence_number)):
                line = l
                break
        if line is not None:
            rating = line[32:37].lstrip()
            if rating == "NC":
                return rating
            else:
                return str(ceil(abs(int(rating)/100))) + ('dan' if int(rating) > 0 else 'kyu' )
    return None
