""" Get data from go Federations"""
from math import log, ceil
import requests

def get_egf_rank(egf_id):
    """
    Check if an EGF id is valid and get_text its rank.
    We return the rank (a string) or None if it's not valid
    """
    url = "https://www.europeangodatabase.eu/EGD/GetPlayerDataByPIN.php?pin=" + str(egf_id)
    request = requests.get(url, timeout=10).json()
    if request['retcode'] == "Ok":
        return request['Grade']
    return None
